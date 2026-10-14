from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pwdlib import PasswordHash
from jose import jwt, JWTError

from database import engine, SessionLocal
from models import Base, Task, User
from schemas import TaskCreate, UserCreate

# ========= Create Database Tables ==========

Base.metadata.create_all(bind=engine)

app = FastAPI()

# ========= Password Hashing ==========

password_hash = PasswordHash.recommended()

# ========= JWT settings ==========

SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# ========= Database Connection ==========

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ========= Home ==========

@app.get("/")
def root():
    return {"message": "Welcome to the Task Management API"}        

# ========== User Registration ==========

@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(User.username == user.username).first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="Uername already exists")

    # Check if email already exists
    existing_email = db.query(User).filter(User.email == user.email).first()
        
    if existing_email:
        raise HTTPException(status_code=400, detail="User email already exists")

    # Hash the password
    hashed_password = password_hash.hash(user.password)

    # Create new user
    new_user = User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_password
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {"message": "User registered successfully", "username": new_user.username, "email": new_user.email}

# ========== Login ==========

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):

    #Find User
    user = db.query(User).filter(User.username == form_data.username).first()

    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    #Verify Password
    password_valid = password_hash.verify(form_data.password, user.hashed_password)

    if not password_valid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Generate JWT token
    access_token = jwt.encode({"sub": user.username}, SECRET_KEY, algorithm=ALGORITHM)

    return {"access_token": access_token, "token_type": "bearer"}

# ========== Get Current User ==========

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        
        return username
    
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
# ========== Current User / Me ==========

@app.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "username": current_user.username, "email": current_user.email}


# ========== Create Task ==========

@app.post("/tasks/")
def create_task(task: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    new_task = Task(
        title=task.title,
        description=task.description,
        completed=task.completed,
        user_id=current_user.id
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    return new_task

# ========== Get all Tasks ==========

@app.get("/tasks/")
def get_tasks(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Task).all()

# ========== Get Single Tasks ==========

@app.get("/tasks/{task_id}")
def get_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return task

# ========== Update Task ==========

@app.put("/tasks/{task_id}")
def update_task(task_id: int, updated_task: TaskCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.title = updated_task.title
    task.description = updated_task.description
    task.completed = updated_task.completed

    db.commit()
    db.refresh(task)

    return task

# ========== Delete Task ==========

@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(Task).filter(Task.id == task_id, Task.user_id == current_user.id).first()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    db.delete(task)
    db.commit()

    return {"message": "Task deleted successfully"}       