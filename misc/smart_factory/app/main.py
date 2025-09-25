from fastapi import FastAPI, Request, Response, Form, Depends, status, Cookie
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text
from typing import Annotated
from hashlib import sha256
import json

from api.api import router
from db.session import get_db

def check_user(UserToken, db: Session):
    query = text('SELECT id, userid, password FROM user')
    users = db.execute(query).all()

    for user in users:
        userdata = {'username':user[1], 'password': user[2]}
        userdata = json.dumps(userdata, sort_keys=True).encode()
        hash_userdata = sha256(userdata).hexdigest()
        
        if hash_userdata == UserToken:
            return True
        
    return False

app = FastAPI()

templates = Jinja2Templates(directory='templates')
app.mount('/static', StaticFiles(directory='static'), name='static')

app.include_router(router)

@app.get('/', response_class=HTMLResponse)
def main_page(request: Request, UserToken: Annotated[str | None, Cookie()] = None, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        'index.html',
        {'request': request, 'login': check_user(UserToken, db)}
    )

@app.get('/product', response_class=HTMLResponse)
def product_page(request: Request, UserToken: Annotated[str | None, Cookie()] = None, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        'product.html',
        {'request': request, 'login': check_user(UserToken, db)}
    )

@app.get('/control', response_class=HTMLResponse)
def control_page(request: Request, UserToken: Annotated[str | None, Cookie()] = None, db: Session = Depends(get_db)):
    return templates.TemplateResponse(
        'control.html',
        {'request': request, 'login': check_user(UserToken, db)}
    )

@app.get('/login', response_class=HTMLResponse)
def login_page(request: Request, UserToken: Annotated[str | None, Cookie()] = None, db: Session = Depends(get_db)):
    success_message = request.query_params.get("registered") == "success"
    error_message = None

    if request.query_params.get("error") == "user_not_found":
        error_message = "사용자명 또는 비밀번호를 다시 확인해주세요."
    elif request.query_params.get("error") == "invalid_password":
        error_message = "사용자명 또는 비밀번호를 다시 확인해주세요."
    return templates.TemplateResponse(
        'login.html',
        {'request': request, 'success_message': success_message, 'error_message': error_message, 'login': check_user(UserToken, db)}
    )

@app.post('/login')
def exec_login(
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    db: Session = Depends(get_db)
):
    if (username == '' or username is None) or (password == '' or password is None):
        return RedirectResponse(url='/login', status_code=status.HTTP_302_FOUND)
    
    user_query = text('SELECT id, userid, password FROM user WHERE userid = :username')
    user = db.execute(user_query, {'username': username}).first()

    if not user:
        return RedirectResponse(url='/login?error=user_not_found', status_code=status.HTTP_303_SEE_OTHER)
    
    hashed_pwd_db = user[2]
    if not (hashed_pwd_db == sha256(password.encode()).hexdigest()):
        return RedirectResponse(url='/login?error=invalid_password', status_code=status.HTTP_303_SEE_OTHER)
    
    userdata = {'username':user[1], 'password': hashed_pwd_db}
    userdata = json.dumps(userdata, sort_keys=True).encode()
    hash_userdata = sha256(userdata).hexdigest()

    response = RedirectResponse(url='/?login=success', status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        key='UserToken',
        value=hash_userdata,
        httponly=True,
        secure=True,
        samesite='lax',
        path='/'
    )

    return response


@app.get('/register', response_class=HTMLResponse)
def login_page(request: Request, UserToken: Annotated[str | None, Cookie()] = None, db: Session = Depends(get_db)):
    error_message = None
    if request.query_params.get("error") == "password_mismatch":
        error_message = "비밀번호와 확인용 비밀번호가 일치하지 않습니다."
    elif request.query_params.get("error") == "none_value":
        error_message = "비어 있는 값이 존재합니다."
    elif request.query_params.get("error") == "user_exists":
        error_message = "이미 존재하는 사용자명입니다."
    elif request.query_params.get("error") == "internal_error":
        error_message = "알 수 없는 오류가 발생했습니다. 다시 시도해주세요."

    return templates.TemplateResponse(
        'register.html',
        {'request': request, 'error_message': error_message, 'login': check_user(UserToken, db)}
    )

@app.post('/register')
def exec_register(
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
    confirm_password: Annotated[str, Form()],
    db: Session = Depends(get_db)
):
    if (username == '' or username is None) or (password == '' or password is None) or (confirm_password == '' or confirm_password is None):
        return RedirectResponse(url='/register?error=none_value', status_code=status.HTTP_303_SEE_OTHER)
    
    if password != confirm_password:
        return RedirectResponse(url='/register?error=password_mismatch', status_code=status.HTTP_303_SEE_OTHER)
    
    check_user = text('SELECT userid FROM user WHERE userid = :username')
    exists = db.execute(check_user, {"username": username}).first()

    if exists:
        return RedirectResponse(url='/register?error=user_exists', status_code=status.HTTP_303_SEE_OTHER)
    
    hashed_pwd = sha256(password.encode()).hexdigest()

    insert_user = text('INSERT INTO user (userid, password) VALUES (:userid, :password)')

    try:
        db.execute(insert_user, {'userid': username, 'password': hashed_pwd})
        db.commit()
    except IntegrityError:
        db.rollback()
        return RedirectResponse(url='/register?error=user_exists', status_code=status.HTTP_303_SEE_OTHER)
    except Exception as e:
        db.rollback()
        print(f'회원가입 오류 : {e}')
        return RedirectResponse(url='/register?error=internal_error', status_code=status.HTTP_303_SEE_OTHER)
    
    return RedirectResponse(url='/login?registered=success', status_code=status.HTTP_303_SEE_OTHER)

@app.get('/logout')
def logout_page():
    response = RedirectResponse(url='/', status_code=status.HTTP_302_FOUND)
    response.delete_cookie(
        key='UserToken'
    )

    return response