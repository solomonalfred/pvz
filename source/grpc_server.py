import asyncio
import grpc
from concurrent import futures
from datetime import datetime, timezone

import pvz_pb2
import pvz_pb2_grpc

def get_all_pvz():
    return [
        {
            "id": "c1d3e9ae-1234-5678-9abc-def123456789",
            "registration_date": datetime(2025, 4, 16, 10, 0, 0, tzinfo=timezone.utc),
            "city": "Москва"
        },
        {
            "id": "d2f3e0ab-2345-6789-abcd-ef2345678901",
            "registration_date": datetime(2025, 4, 16, 11, 30, 0, tzinfo=timezone.utc),
            "city": "Санкт-Петербург"
        },
    ]

class PVZService(pvz_pb2_grpc.PVZServiceServicer):
    def GetPVZList(self, request, context):
        # Получаем все записи ПВЗ
        pvz_list = get_all_pvz()
        # Преобразуем данные в сообщения PVZ
        pvz_messages = []
        for pvz in pvz_list:
            # Преобразуем дату в Timestamp (Message from google.protobuf.timestamp_pb2)
            # Можно использовать метод FromDatetime для преобразования.
            from google.protobuf.timestamp_pb2 import Timestamp
            ts = Timestamp()
            ts.FromDatetime(pvz["registration_date"])
            pvz_msg = pvz_pb2.PVZ(
                id=pvz["id"],
                registration_date=ts,
                city=pvz["city"]
            )
            pvz_messages.append(pvz_msg)
        return pvz_pb2.GetPVZListResponse(pvzs=pvz_messages)

async def serve() -> None:
    server = grpc.aio.server()
    pvz_pb2_grpc.add_PVZServiceServicer_to_server(PVZService(), server)
    listen_addr = "[::]:3000"
    server.add_insecure_port(listen_addr)
    print(f"gRPC сервер запущен на {listen_addr}")
    await server.start()
    await server.wait_for_termination()

if __name__ == "__main__":
    asyncio.run(serve())
