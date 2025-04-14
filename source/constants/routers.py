from enum import StrEnum


class RouterInfo(StrEnum):
    prefix = ""
    auth_tags = "auth"
    pvz_tags = "pvz actions"

class Endpoints(StrEnum):
    DUMMY = "/dummyLogin"
    REGISTRATION = "/register"
    LOGIN = "/login"

    PVZ_END = "/pvz"
    CLOSE_LAST_REC = "/pvz/{pvzId}/close_last_reception"
    DELETE_PRODUCT = "/pvz/{pvzId}/delete_last_product"
    RECEPTIONS = "/receptions"
    PRODUCTS = "/products"
