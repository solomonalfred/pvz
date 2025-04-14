from enum import StrEnum, auto


class RoleType(StrEnum):
    employee = auto()
    moderator = auto()

class ReceptionStatus(StrEnum):
    in_progress = auto()
    close = auto()

class ProductType(StrEnum):
    electonic = "электроника"
    clothes = "одежда"
    shoes = "обувь"

class CityType(StrEnum):
    moscow = "Москва"
    spb = "Санкт-Петербург"
    kazan = "Казань"

if __name__ == "__main__":
    print(RoleType.employee)
