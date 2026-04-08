from fastapi import FastAPI, Request, Query
from fastapi import Form, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import requests
from sqlmodel import SQLModel, create_engine
from sqlmodel import Session, create_engine, select
from models import User  
from models import Transaction, Stock
import bcrypt
from fastapi import Depends, HTTPException, Cookie
from typing import Annotated

sqlite_file_name = "investimentos.db"
sqlite_url = f"sqlite:///{sqlite_file_name}"

engine = create_engine(sqlite_url, echo=True)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

# Certifique-se de que a pasta dos templates existe
templates = Jinja2Templates(directory="templates")

@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return RedirectResponse(url="/login")

@app.get("/login", response_class=HTMLResponse)
async def login(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="login.html"
    )

def verificar_senha(senha, hash):
    return bcrypt.checkpw(senha.encode("utf-8"), hash.encode("utf-8"))


@app.post("/login", response_class=HTMLResponse)
def post_login(request: Request, username: str = Form(...), senha: str = Form(...)):
    with Session(engine) as session:
        usuario = session.exec(
            select(User).where(User.username == username)
        ).first()

        if not (usuario and not verificar_senha(senha, usuario.senha_hash)):
            return HTMLResponse('<p style="color:red">Usuário ou senha incorretos</p>')
        
        response = HTMLResponse()
        response.headers["HX-Redirect"] = "/home"
        response.set_cookie(key="session_user", value=usuario.email)

        return response
    
@app.post("/logout")
def logout():
    response = HTMLResponse()
    response.headers["HX-Redirect"] = "/login"
    response.delete_cookie("session_user")
    return response
    
def get_active_user(session_user: Annotated[str | None, Cookie()] = None):  
    if not session_user:
        return None
    
    with Session(engine) as session:
        usuario = session.exec(
            select(User).where(User.email == session_user)
        ).first()

        if not usuario:
            raise HTTPException(status_code=401, detail="Sessão inválida")

        return usuario

@app.get("/cadastro", response_class=HTMLResponse)
async def cadastro(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="cadastro.html"
    )

def gerar_hash_senha(senha):
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(senha.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def criar_usuario(username, email, senha):
    senha_hash = gerar_hash_senha(senha)
    return User(username=username, email=email, senha_hash=senha_hash)


@app.post("/cadastro")
def post_cadastro_htmx(username: str = Form(...), email: str = Form(...), senha: str = Form(...)):
    try:
        with Session(engine) as session:
            user_exists = session.exec(select(User).where(User.username == username)).first()
            email_exists = session.exec(select(User).where(User.email == email)).first()

            if user_exists or email_exists:
                return HTMLResponse('<p style="color:red">Usuário ou email já cadastrados</p>')

            novo_usuario = criar_usuario(username, email, senha)
            session.add(novo_usuario)
            session.commit()
            return HTMLResponse('<p style="color:green">Cadastro realizado com sucesso!</p>')
    except Exception as e:
        return f"<p>Erro: {e}</p>"

@app.get("/usuarios")
def listar_usuarios():
    with Session(engine) as session:
        usuarios = session.exec(select(User)).all()
        return usuarios

@app.get("/home", response_class=HTMLResponse)
async def home(request: Request, user: User = Depends(get_active_user)):
    if not user:
        return RedirectResponse(url="/login")
    
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "username":user.username
        }
    )

@app.get("/adicionar", response_class=HTMLResponse)
async def adicionar(request: Request, user: User = Depends(get_active_user)):
    if not user:
        return RedirectResponse(url="/login")
    
    return templates.TemplateResponse(
        request=request,
        name="adicionar.html",
        context={
            "username":user.username
        }
    )

@app.get("/perfil", response_class=HTMLResponse)
async def perfil(request: Request, user: User = Depends(get_active_user)):
    if not user:
        return RedirectResponse(url="/login")
    
    return templates.TemplateResponse(
        request=request,
        name="perfil.html",
        context={
            "username":user.username, "email":user.email
        }
    )

@app.put("/username")
async def change_username(request: Request, username : str = Form(...), user : User = Depends(get_active_user)):
    if not user:
        return JSONResponse({"error": "Você precisa estar logado!"}, status_code=401)

    with Session(engine) as session:
        db_user = session.get(User, user.id)
        if not db_user:
            return JSONResponse({"error": "Usuário não encontrado!"}, status_code=404)

        db_user.username = username
        session.add(db_user)
        session.commit()

    return JSONResponse({"status": "ok"})

@app.delete("/delete-account")
async def delete_account(user: User = Depends(get_active_user)):
    if not user:
        return JSONResponse({"error": "not logged"}, status_code=401)

    with Session(engine) as session:
        db_user = session.get(User, user.id)
        if db_user:
            session.delete(db_user)
            session.commit()

    response = JSONResponse({"status": "deleted"})
    response.delete_cookie("session_user")
    return response



def get_preco(ticker):

    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d"

    headers = {
    "User-Agent": "Mozilla/5.0"
    }

    r = requests.get(url, headers=headers)

    data = r.json()


    return data["chart"]["result"][0]["meta"]["regularMarketPrice"]

def busca_no_banco(query : str, page : int):
    with Session(engine) as session:
        page_size = 5
        offset = (page - 1) * page_size

        results = session.exec(
            select(Stock)
            .where(Stock.ticker.startswith(query.upper()))
            .offset(offset)
            .limit(page_size)
        ).all()

        if not results:
            results = []

    return results

@app.get("/acoes", response_class=HTMLResponse)
def listar_acoes(request: Request, query: str = Query(...), page: int = 1, user: User = Depends(get_active_user)):
    if not user:
        return RedirectResponse(url="/login")
    
    results = busca_no_banco(query, page)

    return templates.TemplateResponse(
        request=request,
        name="tabela_acoes.html",
        context={"acoes": results, "request": request, "page": page, "query": query}
    )
    
@app.get("/search", response_class=HTMLResponse)
def search(request: Request, query: str = Query(...), page: int = 1, user: User = Depends(get_active_user)):
    if not user:
        return RedirectResponse(url="/login")
    
    results = busca_no_banco(query, page)

    with Session(engine) as session:
        if not results:
            try:
                preco = get_preco(query + ".SA")
                stock = Stock(ticker=query.upper(), nome=query.upper(), preco=preco)
                session.add(stock)
                session.commit()
                results = [stock]
            except:
                results = []

    return templates.TemplateResponse(
        request=request,
        name="tabela_acoes.html",
        context={"acoes": results, "request": request, "page": page, "query": query}
    )

    
@app.get("/comprar/{ticker}", response_class=HTMLResponse)
async def comprar(request: Request, ticker : str, user: User = Depends(get_active_user)):
    if not user:
        return RedirectResponse(url="/login")
    
    return templates.TemplateResponse(
        request=request,
        name="comprar.html",
        context={
            "ticker": ticker,
            "preco": get_preco(ticker + ".SA")
        }
    )

from fastapi import Form
from datetime import datetime

@app.post("/comprar", response_class=HTMLResponse)
def post_comprar(
    ticker: str = Form(...),
    quantidade: int = Form(...),
    user : User = Depends(get_active_user)
):
    try:
        preco = get_preco(ticker + ".SA")

        with Session(engine) as session:

            stock = session.exec(
                select(Stock).where(Stock.ticker == ticker)
            ).first()

            stock.preco = preco
            stock.ultima_busca = datetime.utcnow()

            transaction = Transaction(
                user_id=user.id,
                ticker=ticker,
                stock_id=stock.id,
                quantidade=quantidade,
                preco_unitario=preco,
                tipo="BUY",
                data=datetime.utcnow()
            )

            session.add(transaction)
            session.commit()

            response = HTMLResponse()
            response.headers["HX-Redirect"] = "/carteira"

        return response

    except Exception as e:
        return f'<p style="color: red">Erro: {e}</p>'
    
@app.get("/transactions")
def listar_transacoes():
    with Session(engine) as session:
        transactions = session.exec(select(Transaction)).all()
        return transactions
    
def montar_carteira(transactions):

    posicoes = {}

    for t in transactions:

        if t.ticker not in posicoes:
            posicoes[t.ticker] = {
                "quantidade": 0,
                "custo": 0
            }

        if t.tipo == "BUY":
            posicoes[t.ticker]["quantidade"] += t.quantidade
            posicoes[t.ticker]["custo"] += t.quantidade * t.preco_unitario

        elif t.tipo == "SELL":
            posicoes[t.ticker]["quantidade"] -= t.quantidade
            posicoes[t.ticker]["custo"] -= t.quantidade * t.preco_unitario

    carteira = []

    for ticker, p in posicoes.items():

        if p["quantidade"] <= 0:
            continue

        preco_medio = p["custo"] / p["quantidade"]

        preco_atual = get_preco(ticker + ".SA")

        valor = p["quantidade"] * preco_atual

        rendimento = valor - p["custo"]

        carteira.append({
            "ticker": ticker,
            "quantidade": round(p["quantidade"], 2),
            "preco_medio": round(preco_medio, 2),
            "preco_atual": round(preco_atual, 2),
            "valor": round(valor, 2),
            "rendimento": round(rendimento, 2)
        })

    return carteira
    
@app.get("/carteira", response_class=HTMLResponse)
async def home(request: Request, user: User = Depends(get_active_user)):
    if not user:
        return RedirectResponse(url="/login")
    
    with Session(engine) as session:
        transactions = session.exec(
            select(Transaction).where(Transaction.user_id == user.id)
        ).all()

    carteira = montar_carteira(transactions)

    total = sum(p["valor"] for p in carteira)

    return templates.TemplateResponse(
        request=request,
        name="carteira.html",
        context={
            "carteira": carteira,
            "total": round(total, 2),
            "username":user.username
        }
    )