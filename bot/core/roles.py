from aiogram.filters import Filter
from aiogram.types import Message, CallbackQuery
from typing import Union, List
from bot.config import settings
from bot.core.constants import UserRole
from bot.db.repositories.users_repo import UsersRepo


class RoleFilter(Filter):
    def __init__(self, allowed_roles: Union[UserRole, List[UserRole]]):
        if isinstance(allowed_roles, UserRole):
            self.allowed_roles = [allowed_roles]
        else:
            self.allowed_roles = allowed_roles

    async def __call__(self, event: Union[Message, CallbackQuery]) -> bool:
        user_id = event.from_user.id
        
        # Super-admin tekshiruvi
        if user_id in settings.ADMIN_IDS:
            if UserRole.ADMIN in self.allowed_roles:
                return True

        user = await UsersRepo.get_by_tg_id(user_id)
        if not user:
            return False

        return user.get("role") in [r.value for r in self.allowed_roles]
