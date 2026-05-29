import uuid
import pytz
from datetime import datetime, timedelta
from typing import Dict, List
from autogen_core.tools import FunctionTool

# Import your Google utilities
from source.google_utils import get_calendar_service
from source.log_records import logger
from source.configurations import config

class CalendarTools:
    """Single class handling all calendar operations."""
    
    def __init__(self):
        self.service = None
        self.default_timezone = config.DEFAULT_TIMEZONE
    
    async def _get_service(self):
        """Get or create calendar service."""
        if self.service is None:
            self.service = get_calendar_service()
        return self.service
    
    def _parse_input(self, input_str: str) -> str:
        """Clean input string by removing surrounding quotes."""
        s = input_str.strip()
        if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
            s = s[1:-1]
        return s
    
    # Public tool methods
    async def list_calendars(self) -> str:
        """List all calendars available in the user's Google Calendar account."""
        try:
            service = await self._get_service()
            calendars = service.calendarList().list().execute().get('items', [])
            summaries = [c['summary'] for c in calendars]
            logger.info(f"Listed {len(summaries)} calendars")
            return "Your calendars:\n" + "\n".join(f"- {s}" for s in summaries)
        except Exception as e:
            logger.error(f"Error listing calendars: {str(e)}")
            return f"Error listing calendars: {str(e)}"
    
    async def create_calendar(self, input_str: str) -> str:
        """Create a new calendar. Input: '<summary> | <timeZone>'"""
        try:
            input_str = self._parse_input(input_str)
            summary, tz = map(str.strip, input_str.split("|"))
            service = await self._get_service()
            calendar = {'summary': summary, 'timeZone': tz}
            created = service.calendars().insert(body=calendar).execute()
            logger.info(f"Created calendar '{summary}' with ID: {created['id']}")
            return f"Created calendar '{summary}' with ID: {created['id']}"
        except Exception as e:
            logger.error(f"Error creating calendar: {str(e)}")
            return f"Error creating calendar: {str(e)}"
    
    async def insert_event(self, input_str: str) -> str:
        """Insert a Meet-enabled event into the primary calendar."""
        try:
            input_str = self._parse_input(input_str)
            parts = [p.strip() for p in input_str.split("|")]
            
            if len(parts) not in (6, 7):
                return ("Invalid input. Expected format:\n"
                       "summary | YYYY-MM-DD | HH:MM | duration-hours | emails | description | [recurrence]")
            
            summary, date_str, time_str, dur, emails, description = parts[:6]
            recurrence = parts[6] if len(parts) == 7 else None
            
            # Parse datetime
            start_dt = datetime.fromisoformat(f"{date_str}T{time_str}")
            end_dt = start_dt + timedelta(hours=float(dur))
            
            # Build event
            event = {
                "summary": summary,
                "description": description,
                "start": {"dateTime": start_dt.isoformat(), "timeZone": self.default_timezone},
                "end": {"dateTime": end_dt.isoformat(), "timeZone": self.default_timezone},
                "attendees": [{"email": e.strip()} for e in emails.split(",") if e.strip()],
                "conferenceData": {
                    "createRequest": {
                        "requestId": str(uuid.uuid4()),
                        "conferenceSolutionKey": {"type": "hangoutsMeet"},
                    }
                },
                "reminders": {"useDefault": True},
            }
            
            # Handle recurrence
            if recurrence:
                rec = recurrence.strip()
                if rec.upper().startswith("RRULE:"):
                    event["recurrence"] = [rec]
                else:
                    toks = rec.lower().split()
                    if toks[0] in ("daily", "weekly") and "until" in toks:
                        freq = toks[0].upper()
                        until_date = toks[-1].replace("-", "") + "T000000Z"
                        event["recurrence"] = [f"RRULE:FREQ={freq};UNTIL={until_date}"]
            
            # Create event
            service = await self._get_service()
            created = service.events().insert(
                calendarId="primary",
                body=event,
                conferenceDataVersion=1,
                sendUpdates="all"
            ).execute()
            
            # Get meet link
            meet_link = (created.get("conferenceData", {})
                        .get("entryPoints", [{}])[0]
                        .get("uri", "No meet link"))
            
            logger.info(f"Created event '{created['summary']}' on {date_str} {time_str}")
            return (f"Created event '{created['summary']}'\n"
                   f"When: {date_str} {time_str} ({dur}h)\n"
                   f"Attendees: {emails}\n"
                   f"Meet: {meet_link}")
            
        except Exception as e:
            logger.error(f"Error creating event: {str(e)}")
            return f"Error creating event: {str(e)}"
    
    async def list_events(self, input_str: str = "primary | 10") -> str:
        """List upcoming events from calendar."""
        try:
            input_str = self._parse_input(input_str)
            cal_id, max_res = map(str.strip, input_str.split("|"))
            max_res = int(max_res)
            
            service = await self._get_service()
            now = datetime.utcnow().isoformat() + "Z"
            
            events = service.events().list(
                calendarId='primary',
                timeMin=now,
                maxResults=max_res,
                singleEvents=True,
                orderBy="startTime"
            ).execute().get("items", [])
            
            if not events:
                logger.info("No upcoming events found")
                return "No upcoming events found."
            
            lines = ["Upcoming events:"]
            for i, event in enumerate(events, 1):
                start = event["start"].get("dateTime", event["start"].get("date"))
                summary = event.get("summary", "(no title)")
                description = event.get("description", "")
                desc_preview = f" - {description[:30]}..." if description else ""
                lines.append(f"{i}. {start}: {summary}{desc_preview}")
            
            logger.info(f"Listed {len(events)} upcoming events")
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Error listing events: {str(e)}")
            return f"Error listing events: {str(e)}"
    
    async def delete_event(self, input_str: str) -> str:
        """Delete an event by title substring."""
        try:
            input_str = self._parse_input(input_str)
            parts = [p.strip() for p in input_str.split("|")]
            query = parts[0].lower()
            scope = "one"
            
            if len(parts) > 1 and parts[1].lower().startswith("scope="):
                scope = parts[1].split("=", 1)[1].strip().lower()
            
            service = await self._get_service()
            now = datetime.utcnow().isoformat() + "Z"
            
            events_result = service.events().list(
                calendarId="primary",
                timeMin=now,
                maxResults=50,
                singleEvents=(scope != "all"),
                orderBy="startTime" if scope != "all" else None
            ).execute()
            
            events = events_result.get("items", [])
            
            for event in events:
                if query in event.get("summary", "").lower():
                    event_id = event["id"]
                    title = event["summary"]
                    
                    service.events().delete(
                        calendarId="primary",
                        eventId=event_id,
                        sendUpdates="all"
                    ).execute()
                    
                    scope_text = "(entire series)" if scope == "all" else ""
                    logger.info(f"Deleted event '{title}' {scope_text}")
                    return f"Deleted event '{title}' {scope_text}"
            
            logger.warning(f"No event found matching '{query}'")
            return f"No event found matching '{query}'"
            
        except Exception as e:
            logger.error(f"Error deleting event: {str(e)}")
            return f"Error deleting event: {str(e)}"
        
    async def get_current_datetime(self) -> str:
        """Get current date and time in the configured timezone."""
        try:
            tz = pytz.timezone(self.default_timezone)
            return datetime.now(tz).isoformat()
        except Exception as e:
            logger.error(f"Error getting current datetime: {str(e)}")
            # Fallback to UTC
            return datetime.now(pytz.UTC).isoformat()
    
    
    async def as_function_tools(self) -> List[FunctionTool]:
        """Convert methods to FunctionTool instances for AutoGen."""
        tools = [
            FunctionTool(
                self.list_calendars,
                description="List all calendars in the user's account"
            ),
            FunctionTool(
                self.create_calendar,
                description="Create a new calendar. Input: '<summary> | <timeZone>'"
            ),
            FunctionTool(
                self.insert_event,
                description=(
                    """
                    Create Meet-enabled events with video conferencing in primary calendar.
                    Input (no quotes): 'summary | YYYY-MM-DD | HH:MM | duration_hours | emails | description | recurrence'
                    Parameters:
                    - summary: Event title
                    - date: YYYY-MM-DD format
                    - time: HH:MM in 24-hour format
                    - duration_hours: Decimal hours (e.g., 0.5 for 30 mins, 1.5 for 90 mins)
                    - emails: Comma-separated attendee emails (no spaces after commas)
                    - description: Event details
                    - recurrence (optional): 'daily until YYYY-MM-DD', 'weekly until YYYY-MM-DD', or raw RRULE
                    Features: Auto-creates Google Meet link, sends invites, sets Asia/Kolkata timezone
                    Examples:
                    insert_event('Team Meeting | 2025-06-15 | 14:30 | 1 | alice@company.com,bob@company.com | Weekly sync meeting')
                    insert_event('Daily Standup | 2025-06-15 | 09:00 | 0.5 | team@company.com | Daily team sync | daily until 2025-12-31')
                    insert_event('Weekly Review | 2025-06-15 | 15:00 | 2 | manager@company.com | Project review | RRULE:FREQ=WEEKLY;BYDAY=FR;COUNT=10')
                    """
                )
            ),
            FunctionTool(
                self.list_events,
                description="""List events from primary calendar by date or number of upcoming events.\n
                                Input formats (no quotes):\n
                                - 'primary | N' - Next N upcoming events from now\n
                                Returns: Event details with start time, title, and description preview (50 chars)\n
                                Examples:\n
                                list_events('primary | 5') - Next 5 upcoming events\n
                                list_events('primary | 1') - Next single event"""            ),
            FunctionTool(
                self.delete_event,
                description="""
                            Delete calendar events by searching title substring from primary calendar.
                            Input (no quotes): '<title_substring>' or '<title_substring> | scope=all'
                            Scope options:
                            - scope=one (default): Delete single occurrence (first match found)
                            - scope=all: Delete entire recurring series
                            Searches upcoming events only, sends deletion notifications to attendees
                            Examples:
                            delete_event('Team Meeting')
                            delete_event('Daily Standup | scope=all')
                            delete_event('Project Review')
                            """

            ),
            FunctionTool(
                self.get_current_datetime,
                description="Get current date and time"
            )
        ]

        return tools
    
# Main function
def create_calendar_tools() -> List[FunctionTool]:
    """Create calendar tools using the single class approach."""
    calendar_tools = CalendarTools()
    return calendar_tools.as_function_tools()


# Testing Standalone File
async def test_calendar_tools():
    """Test the calendar tools."""
    logger.info("Testing Single Class Calendar Tools")
    
    calendar = CalendarTools()
    
    #Test listing calendars
    logger.info("Testing list calendars")
    result = await calendar.list_calendars()
    logger.info(f"List calendars result: {result}")
    
    # Test listing events
    logger.info("Testing list events")
    result = await calendar.list_events("primary | 5")
    logger.info(f"List events result: {result}")
    
    # Test get current time
    logger.info("Testing get current datetime")
    result = await calendar.get_current_datetime()
    logger.info(f"Current time: {result}")
    
    # Test function tools creation
    logger.info("Testing function tools creation")
    tools = await calendar.as_function_tools()
    logger.info(f"Created {len(tools)} tools: {[tool.name for tool in tools]}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_calendar_tools())