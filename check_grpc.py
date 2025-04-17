import asyncio
import grpc
from source import pvz_pb2
from source import pvz_pb2_grpc

async def run():
    async with grpc.aio.insecure_channel('localhost:3000') as channel:
        stub = pvz_pb2_grpc.PVZServiceStub(channel)
        request = pvz_pb2.GetPVZListRequest()
        response = await stub.GetPVZList(request)
        print("Полученный ответ:")
        for pvz in response.pvzs:
            print(f"ID: {pvz.id}, Registration Date: {pvz.registration_date}, City: {pvz.city}")

if __name__ == '__main__':
    asyncio.run(run())
