from engine.correlation import investigate

def handler(request):

    target = request.args.get("target")

    result = investigate(target)

    return {
        "statusCode": 200,
        "body": result
    }
