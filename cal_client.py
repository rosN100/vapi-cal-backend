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
        """Check available appointment slots for a specific date."""
        try:
            # Get event type details
            event_type = await self._get_event_type()
            if not event_type:
                raise Exception("Event type not found")
            
            print(f"DEBUG: Found event type: {event_type.get('title')} (ID: {event_type.get('id')}, slug: {event_type.get('slug')}, teamId: {event_type.get('teamId')})")
            logger.info(f"DEBUG: Found event type: {event_type.get('title')} (ID: {event_type.get('id')}, slug: {event_type.get('slug')}, teamId: {event_type.get('teamId')})")
            
            event_type_id = event_type.get('id')
            team_id = event_type.get('teamId')
            
            if not event_type_id:
                raise Exception("Event type ID not found")
            
            # Convert target date to ISO format for the API
            target_date_str = target_date.strftime('%Y-%m-%d')
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Try different approaches based on whether it's a team event or personal event
            if team_id:
                print(f"DEBUG: This is a team event (teamId: {team_id})")
                logger.info(f"DEBUG: This is a team event (teamId: {team_id})")
                
                # For team events, use the CORRECT Cal.com API v2 /slots/available endpoint
                # Based on research: GET /v2/slots/available with eventTypeId and usernameList[]
                
                # Use the correct /v2/slots/available endpoint with proper parameters
                slots_url = f"{self.base_url}/slots/available"
                
                # Business hours: 9:00 AM - 5:00 PM IST
                # Convert to UTC: IST = UTC+5:30
                # 9:00 AM IST = 3:30 AM UTC, 5:00 PM IST = 11:30 AM UTC
                params = {
                    "eventTypeId": str(event_type_id),  # Event type ID from the found event
                    "eventTypeSlug": event_type.get('slug', 'build3-demo'),  # Event type slug
                    "startTime": f"{target_date_str}T03:30:00Z",  # 9:00 AM IST
                    "endTime": f"{target_date_str}T11:30:00Z",   # 5:00 PM IST
                    "duration": str(event_type.get('length', 30)),  # Duration from event type (default 30)
                    "timeZone": "Asia/Kolkata",  # Team timezone
                    "usernameList[]": ["roshan-flavis", "naman3vedi"]  # Both team members
                }
                
                print(f"DEBUG: Using CORRECT Cal.com v2 /slots/available endpoint with eventTypeId + usernameList")
                print(f"DEBUG: Making GET request to: {slots_url}")
                print(f"DEBUG: Query parameters: {params}")
                print(f"DEBUG: Business hours: 9:00 AM - 5:00 PM IST (3:30 AM - 11:30 AM UTC)")
                print(f"DEBUG: This should return all available slots within business hours")
                
                async with httpx.AsyncClient() as client:
                    response = await client.get(slots_url, params=params, headers=headers)
                    print(f"DEBUG: Slots response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        print(f"DEBUG: Slots response data: {data}")
                        logger.info(f"DEBUG: Slots response: {data}")
                        
                        # Parse the real availability data
                        available_slots = self._process_real_availability(data, target_date)
                        
                        # Format the response as readable text
                        formatted_response = self._format_availability_response(available_slots, target_date)
                        
                        return {
                            "success": True,
                            "target_date": target_date.strftime('%Y-%m-%d'),
                            "available_slots": available_slots,
                            "formatted_response": formatted_response,
                            "message": f"Found {len(available_slots)} available slots"
                        }
                    else:
                        print(f"DEBUG: /slots/available endpoint failed with status: {response.status_code}")
                        print(f"DEBUG: Response body: {response.text}")
                        raise Exception(f"Failed to check team availability: HTTP {response.status_code}")
            else:
                # Personal event - try different endpoints since /slots doesn't exist
                print(f"DEBUG: This is a personal event")
                logger.info(f"DEBUG: This is a personal event")
                
                slots_url = f"{self.base_url}/event-types/{event_type_id}/availability"
                params = {
                    "eventTypeId": str(event_type_id),
                    "startTime": f"{target_date_str}T00:00:00Z",
                    "endTime": f"{target_date_str}T23:59:59Z",
                    "timeZone": "Asia/Calcutta"
                }
                
                async with httpx.AsyncClient() as client:
                    response = await client.get(slots_url, params=params, headers=headers)
                    print(f"DEBUG: Personal event response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        print(f"DEBUG: Personal event response data: {data}")
                        
                        # Parse the real availability data
                        available_slots = self._process_real_availability(data, target_date)
                        
                        # Format the response as readable text
                        formatted_response = self._format_availability_response(available_slots, target_date)
                        
                        return {
                            "success": True,
                            "target_date": target_date.strftime('%Y-%m-%d'),
                            "available_slots": available_slots,
                            "formatted_response": formatted_response,
                            "message": f"Found {len(available_slots)} available slots"
                        }
                    else:
                        print(f"DEBUG: Personal event failed with status: {response.status_code}")
                        print(f"DEBUG: Response body: {response.text}")
                        raise Exception(f"Failed to check personal availability: HTTP {response.status_code}")
                
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
            
            # Use the working structure from successful API call
            booking_data = {
                "start": start_time,
                "attendee": {
                    "name": candidate_name,
                    "email": email_id,
                    "timeZone": "Asia/Kolkata",
                    "language": "en"
                },
                "eventTypeId": event_type["id"],
                "eventTypeSlug": event_type.get("slug", "build3-demo"),
                "username": "roshan-flavis",  # Primary team member
                "teamSlug": "soraaya-team",
                "metadata": {}
            }
            
            print(f"DEBUG: Working booking data structure: {booking_data}")
            
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
                    error_code = error_data.get("error", {}).get("code", "Unknown")
                    
                    # Log the full error response for debugging
                    logger.error(f"Cal.com API v2 error response: {error_data}")
                    print(f"DEBUG: Full error response: {error_data}")
                    
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
                        raise Exception(f"Cal.com API v2 error: {error_message} (Code: {error_code})")
                        
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
            
            # The Cal.com v2 /event-types endpoint returns both personal and team event types
            # Let's use this single endpoint instead of trying separate team endpoints
            logger.info(f"DEBUG: Looking for event type: {self.event_type_slug}")
            print(f"DEBUG: Looking for event type: {self.event_type_slug}")
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Use the main event-types endpoint which returns both personal and team events
            event_types_url = f"{self.base_url}/event-types"
            print(f"DEBUG: Making request to: {event_types_url}")
            logger.info(f"DEBUG: Making request to: {event_types_url}")
            
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(event_types_url, headers=headers)
                    print(f"DEBUG: Event types response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        data = response.json()
                        print(f"DEBUG: Full event types response: {data}")
                        logger.info(f"DEBUG: Full event types response: {data}")
                        
                        # Parse both personal and team event types from the response
                        event_types = []
                        
                        # Get personal event types
                        if data.get("data", {}).get("eventTypeGroups"):
                            for group in data.get("data", {}).get("eventTypeGroups", []):
                                if group.get("teamId") is None:  # Personal events
                                    personal_events = group.get("eventTypes", [])
                                    print(f"DEBUG: Found {len(personal_events)} personal event types")
                                    event_types.extend(personal_events)
                                else:  # Team events
                                    team_events = group.get("eventTypes", [])
                                    team_name = group.get("profile", {}).get("name", "Unknown Team")
                                    print(f"DEBUG: Found {len(team_events)} team event types from {team_name}")
                                    event_types.extend(team_events)
                        
                        print(f"DEBUG: Total event types found: {len(event_types)} items")
                        logger.info(f"DEBUG: Total event types found: {len(event_types)} items")
                        
                        # Find the build3-demo event type
                        for event_type in event_types:
                            event_slug = event_type.get('slug', '')
                            event_title = event_type.get('title', 'Unknown')
                            team_id = event_type.get('teamId')
                            event_type_info = f"{event_title} (slug: {event_slug}, teamId: {team_id})"
                            
                            print(f"DEBUG: Checking event type: {event_type_info}")
                            logger.info(f"DEBUG: Checking event type: {event_type_info}")
                            
                            if event_slug == self.event_type_slug:
                                print(f"Found event type: {event_type}")
                                logger.info(f"Found event type: {event_type}")
                                return event_type
                        
                        print(f"DEBUG: Event type '{self.event_type_slug}' not found in any event types")
                        logger.info(f"DEBUG: Event type '{self.event_type_slug}' not found in any event types")
                        
                    else:
                        print(f"DEBUG: Event types request failed with status: {response.status_code}")
                        logger.info(f"DEBUG: Event types request failed with status: {response.status_code}")
                        
            except Exception as e:
                print(f"DEBUG: Error getting event types: {e}")
                logger.info(f"DEBUG: Error getting event types: {e}")
            
            logger.error(f"Event type '{self.event_type_slug}' not found in any endpoints")
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
    
    def _process_real_availability(self, availability_data: Dict, target_date: date) -> List[Dict]:
        """Process real availability data from Cal.com API v2 /slots/available endpoint."""
        try:
            available_slots = []
            target_date_str = target_date.strftime('%Y-%m-%d')

            print(f"DEBUG: Processing availability data for date: {target_date_str}")
            print(f"DEBUG: Full availability data: {availability_data}")

            # The new /v2/slots/available endpoint returns data in this structure:
            # {"data": {"slots": {"2025-08-22": [{"time": "2025-08-22T04:30:00.000Z"}, ...]}}}
            
            slots_data = availability_data.get("data", {}).get("slots", {})
            print(f"DEBUG: Slots data structure: {slots_data}")

            # Get slots for the specific target date
            date_slots = slots_data.get(target_date_str, [])
            print(f"DEBUG: Found {len(date_slots)} slots for date {target_date_str}")

            for slot in date_slots:
                # Extract start time from the slot data
                start_time = slot.get("time", "")
                if start_time:
                    try:
                        # Parse the ISO time string and convert UTC to IST
                        if isinstance(start_time, str) and "T" in start_time:
                            try:
                                from datetime import datetime, timezone, timedelta
                                
                                # Parse the UTC time from ISO string
                                utc_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                                
                                # Convert to IST (UTC+5:30)
                                ist_timezone = timezone(timedelta(hours=5, minutes=30))
                                ist_time = utc_time.astimezone(ist_timezone)
                                
                                # Extract HH:MM part in IST
                                time_part = ist_time.strftime("%H:%M")
                                
                                # Create slot with 30-minute duration
                                available_slots.append({
                                    "start_time": time_part,
                                    "end_time": self._add_minutes_to_time(time_part, 30),
                                    "available": True
                                })
                                print(f"DEBUG: Converted {start_time} UTC to {time_part} IST")
                            except Exception as e:
                                print(f"DEBUG: Error converting timezone for {start_time}: {e}")
                                # Fallback to original time if conversion fails
                                time_part = start_time.split("T")[1][:5]
                                available_slots.append({
                                    "start_time": time_part,
                                    "end_time": self._add_minutes_to_time(time_part, 30),
                                    "available": True
                                })
                        else:
                            print(f"DEBUG: Skipping slot with invalid time format: {start_time}")
                    except Exception as e:
                        print(f"DEBUG: Error processing slot {slot}: {e}")
                        continue

            print(f"DEBUG: Successfully processed {len(available_slots)} available slots")
            return available_slots

        except Exception as e:
            print(f"DEBUG: Error processing availability data: {e}")
            logger.error(f"Error processing availability data: {e}")
            return []
    
    def _add_minutes_to_time(self, time_str: str, minutes: int) -> str:
        """Add minutes to a time string in HH:MM format."""
        try:
            from datetime import datetime, timedelta
            time_obj = datetime.strptime(time_str, "%H:%M")
            new_time = time_obj + timedelta(minutes=minutes)
            return new_time.strftime("%H:%M")
        except Exception as e:
            print(f"DEBUG: Error adding minutes to time {time_str}: {e}")
            return time_str
    
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