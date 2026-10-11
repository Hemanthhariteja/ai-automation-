from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_business_id, get_owner_business_id
from app.auth.security import hash_password
from app.database.session import get_db
from app.models.business import Business
from app.models.user import User
from app.schemas.business import BusinessProfileResponse, BusinessProfileUpdate
from app.schemas.user import StaffCreate, StaffResponse, StaffUpdate

router = APIRouter(prefix="/api/business", tags=["business"])


def _get_business(db: Session, business_id: int) -> Business:
    business = db.get(Business, business_id)
    if business is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
    return business


@router.get("/profile", response_model=BusinessProfileResponse)
def get_profile(business_id: int = Depends(get_current_business_id), db: Session = Depends(get_db)):
    return _get_business(db, business_id)


@router.patch("/profile", response_model=BusinessProfileResponse)
def update_profile(
    payload: BusinessProfileUpdate,
    business_id: int = Depends(get_owner_business_id),
    db: Session = Depends(get_db),
):
    business = _get_business(db, business_id)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(business, field, value)
    db.commit()
    db.refresh(business)
    return business


@router.get("/staff", response_model=list[StaffResponse])
def list_staff(business_id: int = Depends(get_owner_business_id), db: Session = Depends(get_db)):
    return db.query(User).filter(User.business_id == business_id).order_by(User.id).all()


@router.post("/staff", response_model=StaffResponse, status_code=status.HTTP_201_CREATED)
def create_staff(
    payload: StaffCreate,
    business_id: int = Depends(get_owner_business_id),
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    staff = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role="staff",
        business_id=business_id,
    )
    db.add(staff)
    db.commit()
    db.refresh(staff)
    return staff


@router.patch("/staff/{user_id}", response_model=StaffResponse)
def update_staff(
    user_id: int,
    payload: StaffUpdate,
    business_id: int = Depends(get_owner_business_id),
    db: Session = Depends(get_db),
):
    staff = (
        db.query(User)
        .filter(User.id == user_id, User.business_id == business_id, User.role == "staff")
        .first()
    )
    if staff is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Staff account not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(staff, field, value)
    db.commit()
    db.refresh(staff)
    return staff
