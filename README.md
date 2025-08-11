# Cal.com Webhook API for Vapi AI Agent

This FastAPI application provides webhook endpoints that allow Vapi AI agents to interact with Cal.com calendars for checking availability and booking appointments.

## Features

- **Check Availability**: Webhook endpoint to check available appointment slots in Cal.com calendar
- **Book Appointment**: Webhook endpoint to book appointments with candidate names
- **Configurable**: Environment variables for time ranges, slot durations, and API credentials
- **Error Handling**: Comprehensive error handling and logging
- **FastAPI**: Modern, fast Python web framework with automatic API documentation

## Prerequisites

- Python 3.8+
- Cal.com account with API access
- Cal.com API key
- Access to the "build3-demo" event type

## Installation

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd cal.com-webhook-api
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   cp env.example .env
   ```
   
   Edit `.env` file with your Cal.com credentials:
   ```env
   CAL_API_KEY=your_cal_api_key_here
   CAL_USERNAME=your_cal_username
   CAL_EVENT_TYPE_SLUG=build3-demo
   ```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `CAL_API_KEY` | Your Cal.com API key | Required |
| `CAL_BASE_URL` | Cal.com API base URL | `https://api.cal.com/v1` |
| `CAL_USERNAME` | Your Cal.com username | Required |
| `CAL_EVENT_TYPE_SLUG` | Event type slug to use | `build3-demo` |
| `DEFAULT_TIME_RANGE_DAYS` | Default days to check availability | `7` |
| `DEFAULT_SLOT_DURATION_MINUTES` | Default slot duration | `30` |
| `HOST` | Server host | `0.0.0.0` |
| `PORT` | Server port | `8000` |
| `DEBUG` | Debug mode | `false` |

## Usage

### Running the Server

1. **Development mode**:
   ```bash
   python main.py
   ```

2. **Production mode**:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

3. **With custom port** (useful for Railway):
   ```bash
   uvicorn main:app --host 0.0.0.0 --port $PORT
   ```

### API Endpoints

#### 1. Check Availability

**Endpoint**: `POST /webhook/check-availability`

**Request Body**:
```json
{
  "date": "2024-01-15",
  "time_range_days": 7
}
```

**Response**:
```json
{
  "success": true,
  "date": "2024-01-15",
  "available_slots": [
    {
      "start_time": "09:00",
      "end_time": "09:30",
      "available": true
    },
    {
      "start_time": "09:30",
      "end_time": "10:00",
      "available": true
    }
  ],
  "message": "Found 2 available slots"
}
```

#### 2. Book Appointment

**Endpoint**: `POST /webhook/book-appointment`

**Request Body**:
```json
{
  "date": "2024-01-15",
  "time": "14:30",
  "candidate_name": "John Doe"
}
```

**Response**:
```json
{
  "success": true,
  "booking_id": "abc123",
  "message": "Successfully booked appointment for John Doe",
  "appointment_details": {
    "booking_id": "abc123",
    "start_time": "2024-01-15T14:30:00",
    "end_time": "2024-01-15T15:00:00",
    "title": "Build3<> John Doe",
    "attendees": [...]
  }
}
```

### Health Check Endpoints

- `GET /` - Basic health check
- `GET /health` - Detailed health status

## Vapi AI Agent Integration

### Tool 1: Check Availability

```python
# Vapi tool configuration
{
  "name": "check_calendar_availability",
  "description": "Check available appointment slots in Cal.com calendar",
  "url": "https://your-domain.com/webhook/check-availability",
  "method": "POST",
  "headers": {
    "Content-Type": "application/json"
  }
}
```

### Tool 2: Book Appointment

```python
# Vapi tool configuration
{
  "name": "book_calendar_appointment",
  "description": "Book an appointment in Cal.com calendar",
  "url": "https://your-domain.com/webhook/book-appointment",
  "method": "POST",
  "headers": {
    "Content-Type": "application/json"
  }
}
```

## Deployment

### Railway Deployment (Simplified)

1. **Connect your repository** to Railway
2. **Set environment variables** in Railway dashboard:
   - `CAL_API_KEY`
   - `CAL_USERNAME` 
   - `CAL_EVENT_TYPE_SLUG`
   - `PORT` (Railway will set this automatically)
3. **Deploy** - Railway will automatically detect the Python app and run it

### Environment Variables for Railway

Make sure to set all required environment variables in your Railway project settings. Railway will automatically provide the `PORT` variable.

### Other Platforms

This app can be deployed to any platform that supports Python:
- **Heroku**: Add `Procfile` with `web: uvicorn main:app --host 0.0.0.0 --port $PORT`
- **DigitalOcean App Platform**: Select Python runtime
- **AWS/GCP**: Deploy as Python application
- **VPS**: Run directly with `uvicorn`

## Error Handling

The API includes comprehensive error handling for:

- Invalid date formats
- Past dates
- Invalid time formats
- Cal.com API errors
- Network timeouts
- Configuration validation

All errors return structured JSON responses with appropriate HTTP status codes.

## Logging

The application logs all operations to help with debugging:

- API requests and responses
- Cal.com API interactions
- Error details
- Booking confirmations

## Development

### Project Structure

```
├── main.py              # FastAPI application
├── cal_client.py        # Cal.com API client
├── models.py            # Pydantic data models
├── config.py            # Configuration management
├── requirements.txt     # Python dependencies
├── env.example          # Environment variables template
└── README.md            # This file
```

### Adding New Features

1. **New endpoints**: Add to `main.py`
2. **New models**: Add to `models.py`
3. **New Cal.com features**: Extend `cal_client.py`
4. **Configuration**: Add to `config.py`

## Troubleshooting

### Common Issues

1. **Configuration errors**: Check all environment variables are set
2. **API authentication**: Verify Cal.com API key is valid
3. **Event type not found**: Ensure the event type slug exists
4. **Network issues**: Check Cal.com API accessibility

### Debug Mode

Enable debug mode by setting `DEBUG=true` in your environment variables for detailed logging.

## Support

For issues related to:

- **Cal.com API**: Check [Cal.com API documentation](https://cal.com/docs/developing/introduction)
- **Vapi Integration**: Check [Vapi documentation](https://docs.vapi.ai/tools)
- **This application**: Open an issue in the repository

## License

[Add your license information here] 