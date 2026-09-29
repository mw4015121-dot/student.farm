
import os

from datetime import date, datetime
from typing import Literal

from dotenv import load_dotenv

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.responses import FileResponse

from pydantic import BaseModel, ConfigDict, Field

from sqlalchemy import (
    Date,
    DateTime,
    String,
    Text,
    create_engine,
    func,
    or_,
    select,
    text,
)

from sqlalchemy.engine import make_url

from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
)


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# DATABASE CONNECTION
# DATABASE URL IS STORED IN .env
# ============================================================

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. Please create a .env file."
    )

DB_URL = make_url(DATABASE_URL)


# ============================================================
# CREATE DATABASE IF IT DOES NOT EXIST
# ============================================================

with create_engine(
    DB_URL.set(database=None)
).connect() as conn:

    conn.execute(
        text(
            f"CREATE DATABASE IF NOT EXISTS `{DB_URL.database}` "
            "CHARACTER SET utf8mb4"
        )
    )


# ============================================================
# SQLALCHEMY ENGINE
# ============================================================

engine = create_engine(
    DB_URL,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    bind=engine
)


# ============================================================
# BASE
# ============================================================

class Base(DeclarativeBase):
    pass


# ============================================================
# STUDENT TABLE
# ============================================================

class Student(Base):

    __tablename__ = "students"

    id: Mapped[int] = mapped_column(
        primary_key=True
    )

    full_name: Mapped[str] = mapped_column(
        String(100)
    )

    father_name: Mapped[str] = mapped_column(
        String(100)
    )

    dob: Mapped[date] = mapped_column(
        Date
    )

    gender: Mapped[str] = mapped_column(
        String(10)
    )

    phone: Mapped[str] = mapped_column(
        String(20)
    )

    class_applied: Mapped[str] = mapped_column(
        String(50)
    )

    address: Mapped[str] = mapped_column(
        Text
    )

    status: Mapped[str] = mapped_column(
        String(10),
        default="pending"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now()
    )


# ============================================================
# CREATE TABLES
# ============================================================

Base.metadata.create_all(engine)


# ============================================================
# STUDENT INPUT MODEL
# ============================================================

class StudentIn(BaseModel):

    full_name: str = Field(
        min_length=2,
        max_length=100
    )

    father_name: str = Field(
        min_length=2,
        max_length=100
    )

    dob: date

    gender: Literal[
        "Male",
        "Female"
    ]

    phone: str = Field(
        pattern=r"^[0-9+\- ]{10,20}$"
    )

    class_applied: str = Field(
        min_length=1,
        max_length=50
    )

    address: str = Field(
        min_length=5
    )

    status: Literal[
        "pending",
        "approved",
        "rejected"
    ] = "pending"


# ============================================================
# STUDENT OUTPUT MODEL
# ============================================================

class StudentOut(StudentIn):

    model_config = ConfigDict(
        from_attributes=True
    )

    id: int

    created_at: datetime


# ============================================================
# DATABASE SESSION
# ============================================================

def get_db():

    db = SessionLocal()

    try:
        yield db

    finally:
        db.close()


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI(
    title="Admission Form API"
)


# ============================================================
# HOME PAGE
# ============================================================

@app.get(
    "/",
    include_in_schema=False
)
def home():

    return FileResponse(
        os.path.join(
            os.path.dirname(__file__),
            "index.html"
        )
    )


# ============================================================
# CREATE STUDENT
# ============================================================

@app.post(
    "/api/students",
    response_model=StudentOut,
    status_code=201
)
def create(
    data: StudentIn,
    db: Session = Depends(get_db)
):

    student = Student(
        **data.model_dump()
    )

    db.add(student)

    db.commit()

    db.refresh(student)

    return student


# ============================================================
# GET ALL STUDENTS
# ============================================================

@app.get(
    "/api/students",
    response_model=list[StudentOut]
)
def list_all(
    search: str = "",
    status: str = "",
    db: Session = Depends(get_db)
):

    query = select(
        Student
    ).order_by(
        Student.id.desc()
    )

    if search:

        like = f"%{search}%"

        query = query.where(
            or_(
                Student.full_name.like(like),
                Student.father_name.like(like),
                Student.phone.like(like)
            )
        )

    if status:

        query = query.where(
            Student.status == status
        )

    return db.scalars(query).all()


# ============================================================
# FIND STUDENT
# ============================================================

def find(
    db: Session,
    sid: int
) -> Student:

    student = db.get(
        Student,
        sid
    )

    if not student:

        raise HTTPException(
            status_code=404,
            detail="Application not found"
        )

    return student


# ============================================================
# GET SINGLE STUDENT
# ============================================================

@app.get(
    "/api/students/{sid}",
    response_model=StudentOut
)
def read(
    sid: int,
    db: Session = Depends(get_db)
):

    return find(
        db,
        sid
    )


# ============================================================
# UPDATE STUDENT
# ============================================================

@app.put(
    "/api/students/{sid}",
    response_model=StudentOut
)
def update(
    sid: int,
    data: StudentIn,
    db: Session = Depends(get_db)
):

    student = find(
        db,
        sid
    )

    for key, value in data.model_dump().items():

        setattr(
            student,
            key,
            value
        )

    db.commit()

    db.refresh(student)

    return student


# ============================================================
# DELETE STUDENT
# ============================================================

@app.delete(
    "/api/students/{sid}",
    status_code=204
)
def delete(
    sid: int,
    db: Session = Depends(get_db)
):

    student = find(
        db,
        sid
    )

    db.delete(student)

    db.commit()

    return Response(
        status_code=204
    )
