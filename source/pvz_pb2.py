# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: source/pvz.proto
# Protobuf Python Version: 5.29.0
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC,
    5,
    29,
    0,
    '',
    'source/pvz.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from google.protobuf import timestamp_pb2 as google_dot_protobuf_dot_timestamp__pb2


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x10source/pvz.proto\x12\x06pvz.v1\x1a\x1fgoogle/protobuf/timestamp.proto\"V\n\x03PVZ\x12\n\n\x02id\x18\x01 \x01(\t\x12\x35\n\x11registration_date\x18\x02 \x01(\x0b\x32\x1a.google.protobuf.Timestamp\x12\x0c\n\x04\x63ity\x18\x03 \x01(\t\"\x13\n\x11GetPVZListRequest\"/\n\x12GetPVZListResponse\x12\x19\n\x04pvzs\x18\x01 \x03(\x0b\x32\x0b.pvz.v1.PVZ*P\n\x0fReceptionStatus\x12 \n\x1cRECEPTION_STATUS_IN_PROGRESS\x10\x00\x12\x1b\n\x17RECEPTION_STATUS_CLOSED\x10\x01\x32Q\n\nPVZService\x12\x43\n\nGetPVZList\x12\x19.pvz.v1.GetPVZListRequest\x1a\x1a.pvz.v1.GetPVZListResponseB,Z*github.com/solomonalfred/pvz/pvz_v1;pvz_v1b\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'source.pvz_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  _globals['DESCRIPTOR']._loaded_options = None
  _globals['DESCRIPTOR']._serialized_options = b'Z*github.com/solomonalfred/pvz/pvz_v1;pvz_v1'
  _globals['_RECEPTIONSTATUS']._serialized_start=219
  _globals['_RECEPTIONSTATUS']._serialized_end=299
  _globals['_PVZ']._serialized_start=61
  _globals['_PVZ']._serialized_end=147
  _globals['_GETPVZLISTREQUEST']._serialized_start=149
  _globals['_GETPVZLISTREQUEST']._serialized_end=168
  _globals['_GETPVZLISTRESPONSE']._serialized_start=170
  _globals['_GETPVZLISTRESPONSE']._serialized_end=217
  _globals['_PVZSERVICE']._serialized_start=301
  _globals['_PVZSERVICE']._serialized_end=382
# @@protoc_insertion_point(module_scope)
