import fastavro as avr
import argparse
import json
import os
import base64

class ByteEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, bytes):
            try:
                return int.from_bytes(obj, 'little')
            except Exception:
                return base64.b64encode(obj).decode('ascii')
        return super().default(obj)

def convert(input_file):
    with open(input_file, 'rb') as fo:
        reader = avr.reader(fo)
        records = list(reader)

    base, _ = os.path.splitext(input_file)
    output_file = base + ".json"
    with open(output_file, 'w') as out:
        json.dump(records, out, indent=4, sort_keys=True, cls=ByteEncoder)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Avro to JSON")
    parser.add_argument("input_file", help="Path to the input Avro file")
    args = parser.parse_args()

    convert(args.input_file)