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
            # Use v2 API endpoint /me to get current user info
            url = f"{self.base_url}/me"
            logger.info(f"DEBUG: Getting user ID from base_url: {self.base_url}")
            logger.info(f"DEBUG: Constructed users URL: {url}")
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"Users response: {data}")
                
                if data.get("status") == "success" and data.get("data"):
                    user_data = data.get("data", {})
                    logger.info(f"DEBUG: Extracted user_data: {user_data}")
                    
                    user_id = user_data.get("id")
                    logger.info(f"DEBUG: Looking for user ID in user_data: {user_id}")
                    
                    if user_id:
                        self.user_id = user_id
                        logger.info(f"Found user ID: {user_id} for username: {self.username}")
                        return user_id
                
                logger.error("Failed to get user ID")
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
            event_type = await self._get_event_type()
            if not event_type:
                raise Exception("Failed to get event type details")
            
            # Get availability for the specific date only (not date range)
            start_date = target_date
            end_date = target_date  # Same day only
            
            # Use Cal.com API v2 /slots endpoint
            if event_type.get("teamId"):
                url = f"{self.base_url}/slots"  # Use v2 API
                logger.info(f"DEBUG: Using base_url: {self.base_url}")
                logger.info(f"DEBUG: Constructed slots URL: {url}")
                params = {
                    "eventTypeSlug": event_type.get("slug", "build3-demo"),  # Use event type slug, fallback to build3-demo
                    "teamSlug": "soraaya-team",                              # Your team slug
                    "start": start_date.isoformat(),                          # ISO8601 format
                    "end": end_date.isoformat(),                              # ISO8601 format
                    "timeZone": "Asia/Kolkata"                                # Your timezone
                }
            else:
                url = f"{self.base_url}/slots"  # Use v2 API for personal events too
                logger.info(f"DEBUG: Using base_url: {self.base_url}")
                logger.info(f"DEBUG: Constructed slots URL: {url}")
                params = {
                    "eventTypeSlug": event_type.get("slug", "build3-demo"),
                    "username": self.username,
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                    "timeZone": "Asia/Kolkata"
                }
            
            async with httpx.AsyncClient() as client:
                # Add required headers for Cal.com API v2
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "cal-api-version": "2024-09-04"
                }
                response = await client.get(url, params=params, headers=headers)
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
    
    async def book_appointment(self, target_date: str, time: str, email_id: str) -> dict:
        """Book an appointment using Cal.com API"""
        try:
            # Get user ID for the username
            user_id = await self._get_user_id()
            
            # Get event type details
            event_type = await self._get_event_type()
            if not event_type:
                raise Exception("Event type not found")
            
            # Derive candidate name from email
            candidate_name = self._derive_name_from_email(email_id)
            
            # Create booking data with precise duration matching event type
            # Parse start time and calculate end time using datetime and timedelta
            from datetime import datetime, timedelta
            
            # Combine date and time, assuming time is in HH:MM format (IST)
            # Convert IST to UTC for the API (IST = UTC+5:30)
            from datetime import timezone
            ist_offset = timedelta(hours=5, minutes=30)
            
            start_datetime_str = f"{target_date}T{time}:00"
            start_dt = datetime.fromisoformat(start_datetime_str)
            
            # Convert IST to UTC
            start_dt_utc = start_dt - ist_offset
            
            event_length_minutes = event_type.get("length", 30)
            end_dt_utc = start_dt_utc + timedelta(minutes=event_length_minutes)
            
            start_time = start_dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")  # Format as UTC ISO8601
            
            # Log the exact data being sent for debugging
            logger.info(f"Event type details: {event_type}")
            logger.info(f"Creating booking with start (UTC): {start_time}")
            logger.info(f"Original IST time: {target_date}T{time}:00")
            
            booking_data = {
                "eventTypeId": event_type["id"],
                "start": start_time,
                "attendee": {
                    "email": email_id,
                    "name": candidate_name,
                    "timeZone": "Asia/Kolkata"
                },
                "language": "en",
                "metadata": {},
                "responses": {
                    "email": email_id,
                    "name": candidate_name
                }
            }
            
            # Log the complete booking data
            logger.info(f"Complete booking data: {booking_data}")
            
            # Make booking request using Cal.com API v2
            async with httpx.AsyncClient() as client:
                # Use v2 /bookings endpoint with proper parameters
                headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                    "cal-api-version": "2024-08-13"
                }
                response = await client.post(
                    f"{self.base_url}/bookings",
                    headers=headers,
                    json=booking_data,
                    timeout=30.0
                )
                
                if response.status_code == 201:  # v2 API returns 201 for successful creation
                    booking_info = response.json()
                    data = booking_info.get("data", {})
                    return {
                        "success": True,
                        "booking_id": data.get("uid", "unknown"),
                        "message": "Appointment booked successfully",
                        "appointment_details": {
                            "booking_id": data.get("uid", "unknown"),
                            "start_time": data.get("start", f"{target_date}T{time}:00Z"),
                            "end_time": data.get("end", f"{target_date}T{time}:30Z"),
                            "title": data.get("title", f"Build3<> {candidate_name}"),
                            "attendees": [{"email": email_id, "name": candidate_name}]
                        }
                    }
                else:
                    error_data = response.json()
                    error_message = error_data.get("message", "Unknown error")
                    
                    # Handle specific Cal.com v2 API error cases
                    if error_message == "no_available_users_found_error":
                        raise Exception(
                            "No team members available for this time slot. "
                            "Please check team member availability or contact your administrator."
                        )
                    elif "no_available_users_found_error" in error_message:
                        raise Exception(
                            "No team members are assigned to this event type. "
                            "Please contact your administrator to assign team members."
                        )
                    else:
                        raise Exception(f"Cal.com API v2 error: {error_message}")
                        
        except httpx.HTTPStatusError as e:
            # Log detailed error information
            error_body = ""
            try:
                error_body = e.response.json()
                self.logger.error(f"Cal.com API error response: {error_body}")
            except:
                pass
            
            if e.response.status_code == 400:
                error_message = error_body.get("message", "Bad Request")
                if "no_available_users_found_error" in error_message:
                    raise Exception(
                        "No team members available for this time slot. "
                        "Please check team member availability or contact your administrator."
                    )
                else:
                    raise Exception(f"Cal.com API error: {error_message}")
            else:
                raise Exception(f"HTTP error booking appointment: {e}")
        except Exception as e:
            raise Exception(f"Failed to book appointment: {e}")
    
    async def _get_event_type(self) -> dict:
        """Get event type details by slug."""
        try:
            print(f"DEBUG: Starting _get_event_type for slug: {self.event_type_slug}")
            logger.info(f"DEBUG: Starting _get_event_type for slug: {self.event_type_slug}")
            
            # Since build3-demo is a team event, let's try team endpoints first
            logger.info(f"DEBUG: Looking for team event type: {self.event_type_slug}")
            print(f"DEBUG: Looking for team event type: {self.event_type_slug}")
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # First, try to get teams for the current user
            logger.info(f"DEBUG: Getting teams for current user...")
            print(f"DEBUG: Getting teams for current user...")
            teams_url = f"{self.base_url}/teams"
            
            try:
                async with httpx.AsyncClient() as client:
                    print(f"DEBUG: Making request to: {teams_url}")
                    teams_response = await client.get(teams_url, headers=headers)
                    print(f"DEBUG: Teams response status: {teams_response.status_code}")
                    
                    if teams_response.status_code == 200:
                        teams_data = teams_response.json()
                        print(f"DEBUG: Teams response data: {teams_data}")
                        logger.info(f"DEBUG: Teams response: {teams_data}")
                        
                        # Look for soraaya team
                        teams = teams_data.get("data", []) if teams_data.get("data") else teams_data.get("teams", [])
                        print(f"DEBUG: Found teams: {teams}")
                        logger.info(f"DEBUG: Found teams: {teams}")
                        
                        for team in teams:
                            team_name = team.get("name", "").lower()
                            team_slug = team.get("slug", "").lower()
                            print(f"DEBUG: Checking team: {team_name} (slug: {team_slug})")
                            logger.info(f"DEBUG: Checking team: {team_name} (slug: {team_slug})")
                            
                            # Check if this is the soraaya team
                            if "soraaya" in team_name or "soraaya" in team_slug:
                                team_id = team.get("id")
                                print(f"DEBUG: Found soraaya team with ID: {team_id}")
                                logger.info(f"DEBUG: Found soraaya team with ID: {team_id}")
                                
                                # Try to get team event types using the correct v2 endpoint
                                # Based on Cal.com v2 docs: /v2/teams/{teamId}/event-types
                                team_event_types_url = f"{self.base_url}/teams/{team_id}/event-types"
                                print(f"DEBUG: Trying team event types URL: {team_event_types_url}")
                                logger.info(f"DEBUG: Trying team event types URL: {team_event_types_url}")
                                
                                team_event_types_response = await client.get(team_event_types_url, headers=headers)
                                print(f"DEBUG: Team event types response status: {team_event_types_response.status_code}")
                                
                                if team_event_types_response.status_code == 200:
                                    team_event_types_data = team_event_types_response.json()
                                    print(f"DEBUG: Team event types response data: {team_event_types_data}")
                                    logger.info(f"DEBUG: Team event types response: {team_event_types_data}")
                                    
                                    # Try different response structures
                                    event_types = []
                                    if team_event_types_data.get("data", {}).get("event_types"):
                                        event_types = team_event_types_data.get("data", {}).get("event_types", [])
                                    elif team_event_types_data.get("event_types"):
                                        event_types = team_event_types_data.get("event_types", [])
                                    elif team_event_types_data.get("data"):
                                        event_types = team_event_types_data.get("data", [])
                                    
                                    print(f"DEBUG: Team event types found: {len(event_types)} items")
                                    logger.info(f"DEBUG: Team event types found: {len(event_types)} items")
                                    
                                    # Find the build3-demo event type
                                    for event_type in event_types:
                                        event_slug = event_type.get('slug', '')
                                        print(f"DEBUG: Checking team event type: {event_slug} vs {self.event_type_slug}")
                                        logger.info(f"DEBUG: Checking team event type: {event_slug} vs {self.event_type_slug}")
                                        if event_slug == self.event_type_slug:
                                            print(f"Found team event type: {event_type}")
                                            logger.info(f"Found team event type: {event_type}")
                                            return event_type
                                    
                                    print(f"DEBUG: Event type '{self.event_type_slug}' not found in soraaya team")
                                    logger.info(f"DEBUG: Event type '{self.event_type_slug}' not found in soraaya team")
                                else:
                                    print(f"DEBUG: Team event types request failed with status: {team_event_types_response.status_code}")
                                    logger.info(f"DEBUG: Team event types request failed with status: {team_event_types_response.status_code}")
                                
                                break  # Found soraaya team, no need to check others
                    else:
                        print(f"DEBUG: Teams request failed with status: {teams_response.status_code}")
                        logger.info(f"DEBUG: Teams request failed with status: {teams_response.status_code}")
                        
            except Exception as e:
                print(f"DEBUG: Error getting teams: {e}")
                logger.info(f"DEBUG: Error getting teams: {e}")
            
            print(f"DEBUG: Team approach failed, trying personal event types...")
            logger.info(f"DEBUG: Team approach failed, trying personal event types...")
            
            # If team approach failed, fall back to personal event types
            logger.info(f"DEBUG: Team approach failed, trying personal event types...")
            
            # Get user ID for personal endpoints
            user_id = await self._get_user_id()
            if not user_id:
                raise Exception("Failed to get user ID")
            
            print(f"DEBUG: Got user ID: {user_id}")
            logger.info(f"DEBUG: Got user ID: {user_id}")
            
            # Try multiple possible personal endpoint structures based on Cal.com v2 docs
            possible_endpoints = [
                f"{self.base_url}/event-types",  # Basic endpoint
                f"{self.base_url}/users/{user_id}/event-types",  # User-specific
                f"{self.base_url}/me/event-types",  # Current user
                f"{self.base_url}/event-types?userId={user_id}"  # With query param
            ]
            
            for endpoint_url in possible_endpoints:
                print(f"DEBUG: Trying personal endpoint: {endpoint_url}")
                logger.info(f"DEBUG: Trying personal endpoint: {endpoint_url}")
                
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.get(endpoint_url, headers=headers)
                        
                        if response.status_code == 200:
                            print(f"DEBUG: SUCCESS with personal endpoint: {endpoint_url}")
                            logger.info(f"DEBUG: SUCCESS with personal endpoint: {endpoint_url}")
                            data = response.json()
                            print(f"DEBUG: Full personal event types response: {data}")
                            logger.info(f"DEBUG: Full personal event types response: {data}")
                            
                            # Try different response structures
                            event_types = []
                            if data.get("data", {}).get("event_types"):
                                event_types = data.get("data", {}).get("event_types", [])
                            elif data.get("event_types"):
                                event_types = data.get("event_types", [])
                            elif data.get("data"):
                                event_types = data.get("data", [])
                            
                            print(f"DEBUG: Personal event types found: {len(event_types)} items")
                            logger.info(f"DEBUG: Personal event types found: {len(event_types)} items")
                            
                            # Find the build3-demo event type
                            for event_type in event_types:
                                event_slug = event_type.get('slug', '')
                                print(f"DEBUG: Checking personal event type: {event_slug} vs {self.event_type_slug}")
                                logger.info(f"DEBUG: Checking personal event type: {event_slug} vs {self.event_type_slug}")
                                if event_slug == self.event_type_slug:
                                    print(f"Found personal event type: {event_type}")
                                    logger.info(f"Found personal event type: {event_type}")
                                    return event_type
                            
                            print(f"DEBUG: Event type '{self.event_type_slug}' not found in this personal endpoint")
                            logger.info(f"DEBUG: Event type '{self.event_type_slug}' not found in this personal endpoint")
                            continue  # Try next endpoint
                            
                        else:
                            print(f"DEBUG: Personal endpoint {endpoint_url} returned status: {response.status_code}")
                            logger.info(f"DEBUG: Personal endpoint {endpoint_url} returned status: {response.status_code}")
                            continue  # Try next endpoint
                            
                except Exception as e:
                    print(f"DEBUG: Error with personal endpoint {endpoint_url}: {e}")
                    logger.info(f"DEBUG: Error with personal endpoint {endpoint_url}: {e}")
                    continue  # Try next endpoint
            
            print(f"DEBUG: Event type '{self.event_type_slug}' not found in any endpoints (team or personal)")
            logger.error(f"Event type '{self.event_type_slug}' not found in any endpoints (team or personal)")
            raise Exception(f"Event type '{self.event_type_slug}' not found")
            
        except Exception as e:
            print(f"DEBUG: Error in _get_event_type: {e}")
            logger.error(f"Error getting event type details: {e}")
            raise Exception(f"Failed to get event type details: {e}")
    
    async def _get_user_info(self) -> Optional[Dict]:
        """Get full user information including organization details."""
        try:
            url = f"{self.base_url}/me"
            logger.info(f"DEBUG: Getting user info from: {url}")
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"DEBUG: User info response: {data}")
                
                if data.get("status") == "success" and data.get("data"):
                    user_data = data.get("data", {})
                    logger.info(f"DEBUG: Extracted user_data: {user_data}")
                    return user_data
                
                return None
            
        except Exception as e:
            logger.error(f"Error getting user info: {e}")
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

    def _derive_name_from_email(self, email_id: str) -> str:
        """Derive a human-readable name from email address"""
        # Extract the part before @ and replace dots with spaces
        name_part = email_id.split('@')[0]
        # Replace dots with spaces and capitalize each word
        return name_part.replace('.', ' ').title() 