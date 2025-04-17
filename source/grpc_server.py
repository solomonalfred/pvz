import asyncio
import grpc
from sqlalchemy import select
from source.db.models import PVZTable
from source.db.engine import get_async_session

import pvz_pb2
import pvz_pb2_grpc
from google.protobuf.timestamp_pb2 import Timestamp


class PVZService(pvz_pb2_grpc.PVZServiceServicer):
    async def GetPVZList(self, request, context):
        async with get_async_session() as session:
            stmt = select(PVZTable)
            result = await session.execute(stmt)
            pvz_objs = result.scalars().all()

            pvz_messages = []
            for obj in pvz_objs:
                ts = Timestamp()
                ts.FromDatetime(obj.registrationDate)
                pvz_messages.append(
                    pvz_pb2.PVZ(
                        id=str(obj.id),
                        registration_date=ts,
                        city=obj.city.value
                    )
                )

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
