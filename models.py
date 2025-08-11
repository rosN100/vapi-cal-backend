from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime, date

class CheckAvailabilityRequest(BaseModel):
    target_date: date = Field(..., description="Date to check availability for (YYYY-MM-DD)")
    time_range_days: Optional[int] = Field(None, description="Number of days to check (default from env)")

class TimeSlot(BaseModel):
    start_time: str = Field(..., description="Start time in HH:MM format")
    end_time: str = Field(..., description="End time in HH:MM format")
    available: bool = Field(..., description="Whether the slot is available")

class CheckAvailabilityResponse(BaseModel):
    success: bool = Field(..., description="Whether the request was successful")
    target_date: date = Field(..., description="Date checked")
    available_slots: List[TimeSlot] = Field(..., description="List of available time slots")
    message: Optional[str] = Field(None, description="Additional message or error details")

class BookAppointmentRequest(BaseModel):
    target_date: date = Field(..., description="Date for the appointment (YYYY-MM-DD)")
    time: str = Field(..., description="Start time in HH:MM format")
    candidate_name: str = Field(..., description="Name of the candidate")

class BookAppointmentResponse(BaseModel):
    success: bool = Field(..., description="Whether the booking was successful")
    booking_id: Optional[str] = Field(None, description="Cal.com booking ID if successful")
    message: str = Field(..., description="Success or error message")
    appointment_details: Optional[dict] = Field(None, description="Details of the booked appointment")

class ErrorResponse(BaseModel):
    success: bool = Field(False, description="Always false for error responses")
    error: str = Field(..., description="Error message")
    details: Optional[str] = Field(None, description="Additional error details") 