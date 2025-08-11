from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
from datetime import date, datetime
from typing import List

from config import settings
from models import (
    CheckAvailabilityRequest, 
    CheckAvailabilityResponse, 
    BookAppointmentRequest, 
    BookAppointmentResponse,
    TimeSlot,
    ErrorResponse
)
from cal_client import CalClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Cal.com Webhook API",
    description="Webhook endpoints for Vapi AI agent to interact with Cal.com calendar",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Cal.com client
cal_client = CalClient()

@app.on_event("startup")
async def startup_event():
    """Validate configuration on startup"""
    try:
        logger.info("Starting up Cal.com Webhook API...")
        logger.info(f"Cal.com API configured for user: {settings.cal_username}")
        logger.info(f"Event type: {settings.cal_event_type_slug}")
        logger.info(f"PORT environment variable: {os.getenv('PORT', 'NOT SET')}")
        logger.info(f"Railway PORT: {os.getenv('PORT', 'NOT SET')}")
        logger.info("Startup completed successfully")
    except Exception as e:
        logger.error(f"Startup error: {e}")
        # Don't crash on startup - just log the error
        logger.warning("Continuing with startup despite configuration issues")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "Cal.com Webhook API is running",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

@app.post("/webhook/check-availability", response_model=CheckAvailabilityResponse)
async def check_availability(request: CheckAvailabilityRequest):
    """
    Webhook endpoint for Vapi AI agent to check calendar availability
    
    Args:
        request: Contains the target_date to check and optional time range
        
    Returns:
        Available time slots for the specified date range
    """
    try:
        logger.info(f"Checking availability for date: {request.target_date}")
        
        # Validate date is not in the past
        if request.target_date < date.today():
            raise HTTPException(
                status_code=400, 
                detail="Cannot check availability for past dates"
            )
        
        # Check availability using Cal.com client
        available_slots = await cal_client.check_availability(
            target_date=request.target_date,
            time_range_days=request.time_range_days
        )
        
        # Convert to TimeSlot models
        time_slots = []
        for slot in available_slots:
            time_slots.append(TimeSlot(
                start_time=slot["start_time"],
                end_time=slot["end_time"],
                available=slot["available"]
            ))
        
        return CheckAvailabilityResponse(
            success=True,
            target_date=request.target_date,
            available_slots=time_slots,
            message=f"Found {len(time_slots)} available slots"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking availability: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check availability: {str(e)}"
        )

@app.post("/webhook/book-appointment", response_model=BookAppointmentResponse)
async def book_appointment(request: BookAppointmentRequest):
    """
    Webhook endpoint for Vapi AI agent to book an appointment
    
    Args:
        request: Contains the target_date, time, and candidate name
        
    Returns:
        Confirmation of the booking with details
    """
    try:
        logger.info(f"Booking appointment for {request.candidate_name} on {request.target_date} at {request.time}")
        
        # Validate date is not in the past
        if request.target_date < date.today():
            raise HTTPException(
                status_code=400, 
                detail="Cannot book appointments for past dates"
            )
        
        # Validate time format
        try:
            datetime.strptime(request.time, "%H:%M")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid time format. Please use HH:MM format (e.g., 14:30)"
            )
        
        # Book appointment using Cal.com client
        booking_result = await cal_client.book_appointment(
            appointment_date=request.target_date,
            appointment_time=request.time,
            candidate_name=request.candidate_name
        )
        
        return BookAppointmentResponse(
            success=True,
            booking_id=booking_result.get("booking_id"),
            message=f"Successfully booked appointment for {request.candidate_name}",
            appointment_details=booking_result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error booking appointment: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to book appointment: {str(e)}"
        )

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal server error",
            details=str(exc)
        ).dict()
    )

if __name__ == "__main__":
    import uvicorn
    # Use Railway's PORT environment variable or default to 8000
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False  # Disable reload in production
    ) 