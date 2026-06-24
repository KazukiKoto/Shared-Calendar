from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import CurrentUser
from app.core.database import get_db
from app.schemas.auth import UpdateUserRequest, UserDetailResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserDetailResponse)
async def get_me(user: CurrentUser) -> UserDetailResponse:
    return UserDetailResponse.model_validate(user)


@router.patch("/me", response_model=UserDetailResponse)
async def update_me(
    data: UpdateUserRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: CurrentUser,
) -> UserDetailResponse:
    if data.name is not None:
        user.name = data.name
    if data.timezone is not None:
        user.timezone = data.timezone
    user.updated_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(user)
    return UserDetailResponse.model_validate(user)
