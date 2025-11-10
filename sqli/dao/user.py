from typing import NamedTuple, Optional
from aiopg import Connection
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError


class User(NamedTuple):
    id: int
    first_name: str
    middle_name: Optional[str]
    last_name: str
    username: str
    pwd_hash: str
    is_admin: bool

    @classmethod
    def from_raw(cls, raw: tuple):
        return cls(*raw) if raw else None

    @staticmethod
    async def get(conn: Connection, id_: int):
        async with conn.cursor() as cur:
            await cur.execute(
                'SELECT id, first_name, middle_name, last_name, '
                'username, pwd_hash, is_admin FROM users WHERE id = %s',
                (id_,),
            )
            return User.from_raw(await cur.fetchone())

    @staticmethod
    async def get_by_username(conn: Connection, username: str):
        async with conn.cursor() as cur:
            await cur.execute(
                'SELECT id, first_name, middle_name, last_name, '
                'username, pwd_hash, is_admin FROM users WHERE username = %s',
                (username,),
            )
            return User.from_raw(await cur.fetchone())

    def check_password(self, password: str) -> bool:
        """
        Verify password using Argon2 password hashing.
        
        Args:
            password: Plain text password to verify
            
        Returns:
            True if password matches, False otherwise
        """
        ph = PasswordHasher()
        try:
            ph.verify(self.pwd_hash, password)
            return True
        except VerifyMismatchError:
            return False

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password for secure storage using Argon2.
        
        Args:
            password: Plain text password to hash
            
        Returns:
            Hashed password string safe for database storage
        """
        ph = PasswordHasher()
        return ph.hash(password)

    async def update_password(self, conn: Connection, new_password: str) -> None:
        """
        Update user's password in the database.
        
        Args:
            conn: Database connection
            new_password: New plain text password to set
        """
        new_hash = self.hash_password(new_password)
        async with conn.cursor() as cur:
            await cur.execute(
                'UPDATE users SET pwd_hash = %s WHERE id = %s',
                (new_hash, self.id),
            )
