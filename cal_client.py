import httpx
from typing import List, Dict, Optional
from datetime import datetime, date, timedelta
import logging
from config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CalClient:
    def __init__(self):
        self.api_key = settings.cal_api_key
        self.base_url = settings.cal_base_url
        self.username = settings.cal_username
        self.event_type_slug = settings.cal_event_type_slug
        self.team_id = 85823  # Use team ID instead of slug
        self.user_id = None  # Will be fetched on first use
        self.headers = {
            "Content-Type": "application/json"
        }
    
    async def _get_user_id(self) -> Optional[int]:
        """Get user ID from Cal.com API"""
        if self.user_id:
            return self.user_id
            
        try:
            url = f"{self.base_url}/users"
            params = {"apiKey": self.api_key}
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"Users response: {data}")
                
                # Find user by username
                for user in data.get("users", []):
                    if user.get("username") == self.username:
                        self.user_id = user.get("id")
                        logger.info(f"Found user ID: {self.user_id} for username: {self.username}")
                        return self.user_id
                
                logger.error(f"User '{self.username}' not found")
                return None
                
        except Exception as e:
            logger.error(f"Error getting user ID: {e}")
            return None
    
    async def check_availability(self, target_date: date, time_range_days: int = None) -> Dict:
        """Check availability for a specific date range"""
        if time_range_days is None:
            time_range_days = settings.default_time_range_days
            
        try:
            # Get user ID first
            user_id = await self._get_user_id()
            if not user_id:
                raise Exception("Failed to get user ID")
            
            # Get event type details
            event_type = await self._get_event_type(user_id)
            if not event_type:
                raise Exception("Failed to get event type details")
            
            # Get availability for the date range
            start_date = target_date
            end_date = target_date + timedelta(days=time_range_days)
            
            # Use team availability endpoint for team events
            if event_type.get("teamId"):
                url = f"{self.base_url}/availability"
                params = {
                    "apiKey": self.api_key,
                    "teamId": self.team_id,
                    "eventTypeSlug": self.event_type_slug,
                    "dateFrom": start_date.isoformat(),
                    "dateTo": end_date.isoformat(),
                    "duration": settings.default_slot_duration_minutes
                }
            else:
                url = f"{self.base_url}/users/{user_id}/availability"
                params = {
                    "apiKey": self.api_key,
                    "eventTypeId": event_type["id"],
                    "dateFrom": start_date.isoformat(),
                    "dateTo": end_date.isoformat(),
                    "duration": settings.default_slot_duration_minutes
                }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"Availability response: {data}")
                
                # Process availability data
                available_slots = self._process_availability(data, target_date)
                
                # Format the response as readable text
                formatted_response = self._format_availability_response(available_slots, target_date)
                
                return {
                    "success": True,
                    "target_date": target_date.strftime('%Y-%m-%d'),
                    "available_slots": available_slots,
                    "formatted_response": formatted_response,
                    "message": f"Found {len(available_slots)} available slots"
                }
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error checking availability: {e}")
            raise Exception(f"Failed to check availability: {e}")
        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            raise Exception(f"Failed to check availability: {e}")
    
    async def book_appointment(self, appointment_date: date, appointment_time: str, candidate_name: str) -> Dict:
        """Book an appointment using Cal.com API"""
        try:
            # Get user ID first
            user_id = await self._get_user_id()
            if not user_id:
                raise Exception("Failed to get user ID")
            
            # Get event type details
            event_type = await self._get_event_type(user_id)
            if not event_type:
                raise Exception("Failed to get event type details")
            
            # Create booking - use the main bookings endpoint
            url = f"{self.base_url}/bookings"
            params = {"apiKey": self.api_key}
            
            # Parse time and create datetime
            time_obj = datetime.strptime(appointment_time, "%H:%M").time()
            start_datetime = datetime.combine(appointment_date, time_obj)
            end_datetime = start_datetime + timedelta(minutes=settings.default_slot_duration_minutes)
            
            # Create call title
            call_title = f"Build3<> {candidate_name}"
            
            # Updated booking data structure based on Cal.com API docs
            booking_data = {
                "eventTypeId": event_type["id"],
                "start": start_datetime.isoformat(),
                "end": end_datetime.isoformat(),
                "attendees": [
                    {
                        "email": f"{candidate_name.lower().replace(' ', '.')}@example.com",
                        "name": candidate_name
                    }
                ],
                "title": call_title,
                "description": f"Build3 demo call with {candidate_name}",
                "timeZone": "UTC",
                "language": "en",
                "metadata": {},
                "responses": {
                    "email": f"{candidate_name.lower().replace(' ', '.')}@example.com",
                    "name": candidate_name
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, params=params, json=booking_data)
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"Booking response: {data}")
                
                return {
                    "booking_id": data.get("uid"),
                    "start_time": data.get("startTime"),
                    "end_time": data.get("endTime"),
                    "title": data.get("title"),
                    "attendees": data.get("attendees", [])
                }
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error booking appointment: {e}")
            # Log the response body for debugging
            if hasattr(e, 'response') and e.response:
                try:
                    error_body = e.response.json()
                    logger.error(f"Cal.com API error response: {error_body}")
                except:
                    logger.error(f"Cal.com API error response: {e.response.text}")
            raise Exception(f"Failed to book appointment: {e}")
        except Exception as e:
            logger.error(f"Error booking appointment: {e}")
            raise Exception(f"Failed to book appointment: {e}")
    
    async def _get_event_type(self, user_id: int) -> Optional[Dict]:
        """Get event type details - handle both personal and team events"""
        try:
            # First try team events using team ID
            team_url = f"{self.base_url}/teams/{self.team_id}/event-types"
            team_params = {"apiKey": self.api_key}
            
            async with httpx.AsyncClient() as client:
                response = await client.get(team_url, params=team_params)
                if response.status_code == 200:
                    data = response.json()
                    event_types = data.get("event_types", [])
                    
                    # Find the build3-demo event type
                    for event_type in event_types:
                        if event_type.get("slug") == self.event_type_slug:
                            logger.info(f"Found team event type: {event_type}")
                            return event_type
                
                # Fallback to personal events if team event not found
                personal_url = f"{self.base_url}/users/{user_id}/event-types"
                personal_params = {"apiKey": self.api_key}
                
                response = await client.get(personal_url, params=personal_params)
                response.raise_for_status()
                
                data = response.json()
                event_types = data.get("event_types", [])
                
                for event_type in event_types:
                    if event_type.get("slug") == self.event_type_slug:
                        return event_type
                
                logger.error(f"Event type '{self.event_type_slug}' not found in personal or team events")
                return None
                
        except Exception as e:
            logger.error(f"Error getting event type: {e}")
            return None
    
    def _process_availability(self, availability_data: Dict, target_date: date) -> List[Dict]:
        """Process availability data and return available time slots"""
        available_slots = []
        
        try:
            # Extract availability information
            # Note: The exact structure depends on Cal.com API response
            # This is a generic implementation that you may need to adjust
            
            # Assuming the API returns available time slots
            if "available_slots" in availability_data:
                for slot in availability_data["available_slots"]:
                    available_slots.append({
                        "start_time": slot.get("start_time"),
                        "end_time": slot.get("end_time"),
                        "available": True
                    })
            else:
                # If no specific slots, generate default business hours
                # You can customize this based on your needs
                business_hours = self._generate_business_hours(target_date)
                available_slots.extend(business_hours)
            
            return available_slots
            
        except Exception as e:
            logger.error(f"Error processing availability: {e}")
            return []
    
    def _format_availability_response(self, available_slots: List[Dict], target_date: date) -> str:
        """Format availability response as readable text"""
        if not available_slots:
            return f"No available slots found for {target_date.strftime('%Y-%m-%d')}"
        
        # Extract start times and format them
        start_times = [slot["start_time"] for slot in available_slots if slot.get("available")]
        
        # Format the response
        formatted_response = f"Available slots for {target_date.strftime('%Y-%m-%d')}:\n"
        formatted_response += ", ".join(start_times)
        formatted_response += f"\n\nTotal: {len(start_times)} slots available"
        
        return formatted_response
    
    def _generate_business_hours(self, target_date: date) -> List[Dict]:
        """Generate default business hours for a given date"""
        slots = []
        start_hour = 9  # 9 AM
        end_hour = 17   # 5 PM
        
        for hour in range(start_hour, end_hour):
            for minute in [0, 30]:  # 30-minute slots
                start_time = f"{hour:02d}:{minute:02d}"
                end_hour_calc = hour
                end_minute = minute + 30
                if end_minute >= 60:
                    end_hour_calc += 1
                    end_minute = 0
                end_time = f"{end_hour_calc:02d}:{end_minute:02d}"
                
                slots.append({
                    "start_time": start_time,
                    "end_time": end_time,
                    "available": True
                })
        
        return slots 