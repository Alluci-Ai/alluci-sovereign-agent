from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from ..security.auth import verify_authenticated

router = APIRouter()

templates = Jinja2Templates(directory="backend/templates")

@router.get("/", response_class=HTMLResponse, dependencies=[Depends(verify_authenticated)])
async def get_monitoring_page(request: Request):
    """Serve the premium monitoring UI page."""
    return templates.TemplateResponse("monitor.html", {"request": request})
