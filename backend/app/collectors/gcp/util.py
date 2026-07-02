from google.protobuf.json_format import MessageToDict


def proto_to_dict(resource) -> dict:
    return MessageToDict(resource._pb)
