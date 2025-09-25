from fastapi import APIRouter
from fastapi.responses import JSONResponse
import datetime

router = APIRouter(
    prefix='/api',
    tags=['api']
)

manufact_data = {
    'paper' : {
        '1-1': True,
        '1-2': True,
        '3-1': True,
        '4-2': False,
    },
    'leather' : {
        '2-1': True,
        '3-2': False,
        '4-1': True,
    },
    'pencil' : {
        '2-2': True,
        '5-1': True,
        '5-2': False
    }
}

material_production_targets = {
    'paper': 1000,
    'leather': 500,
    'pencil': 200
}

summary_data = {
    "total_produced_today": 1250,
    "daily_target": sum(material_production_targets.values()),
    "current_efficiency": 83.3,
    "total_errors": 5,
    "unresolved_errors": 2,
    "last_updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
}

def filter(exp):
    blacklist = ['os', "'", '"']

    for char in blacklist:
        if char in exp:
            return False
        
    return True

@router.get('/manufact')
def get_manufact_status():
    return JSONResponse(content=manufact_data)

@router.get("/production_status")
async def get_production_status():
    summary_data["daily_target"] = sum(material_production_targets.values())
    response_data = {
        "manufact_lines": manufact_data,
        "summary": summary_data,
        "material_targets": material_production_targets
    }
    return JSONResponse(content=response_data)

@router.post("/line_control")
def update_line_status(line_data: dict):
    material = line_data.get("material")
    coordinate = line_data.get("coordinate")
    enabled = line_data.get("enabled")

    if material in manufact_data and coordinate in manufact_data[material]:
        manufact_data[material][coordinate] = bool(enabled)
        return {"status": "success", "message": "Line status updated."}
    return {"status": "error", "message": "Line not found or invalid data."}, 404

@router.post("/set_target")
def set_material_target(target_data: dict):
    material = target_data.get("material")
    new_target = target_data.get("target_amount")

    if material not in material_production_targets:
        return {"status": "error", "message": f"Material '{material}' not found."}, 400

    if isinstance(new_target, (int, float)) and new_target >= 0:
        material_production_targets[material] = int(new_target)
        summary_data["daily_target"] = sum(material_production_targets.values())
        return {"status": "success", "message": f"Production target for {material} updated."}
    return {"status": "error", "message": "Invalid target amount."}, 400

@router.post("/calculate")
def calculate_expression(data: dict):
    expression = data.get("expression")
    if not expression:
        return {"error": "No expression provided."}, 400
    
    if not filter(expression):
        return {"error": "No hack!"}, 400
    
    try:
        result = eval(expression, {'__builtins__': None})
        return {"result": str(result)}
    except Exception as e:
        return {"error": f"Invalid expression: {e}"}, 400