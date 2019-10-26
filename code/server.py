import iconclass
from flask import Flask, Response, redirect, request, abort
import json

app = Flask(__name__)


@app.route("/api/iconclass")
def main():
    notations = request.args.getlist("notation")
    tmp = iconclass.get_list(notations)

    return Response(json.dumps(tmp, indent=2), mimetype="text/json")

    # notations = request.GET.getlist("notation", [])
    # tmp = {}
    # for x in util.get_iconclass_list(notations, filled=False):
    #     tmp[x["n"]] = x

    # return json_response(tmp)


@app.route("/")
def home():
    return "OK"


if __name__ == "__main__":
    try:
        port = int(sys.argv[1])
    except:
        port = 50055
    try:
        host = sys.argv[2]
    except:
        host = "127.0.0.1"
    app.run(port=port, host=host)

