from passlib.context import CryptContext


# Todo: потом убрать предупреждение о версии
class PasswordManager:
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    def hash_password(self, password) -> str:
        return self.pwd_context.hash(password)

    def verify_password(self, password, hashed_password) -> bool:
        return self.pwd_context.verify(password, hashed_password)


if __name__ == '__main__':
    hasher = PasswordManager()
    hash_ = hasher.hash_password('12345')
    print(hasher.verify_password('12345', hash_))
