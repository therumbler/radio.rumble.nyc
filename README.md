# Feed Builder

This is a simple Python project which builds RSS XML and [JSON feeds](https://www.jsonfeed.org/) for radio.rumble.nyc.

It uses the [uv package manager](https://docs.astral.sh/uv/).

## How-To

1. install uv [per the instructions](https://docs.astral.sh/uv/#installation)

2. Setup the virtual environment

```
uv venv
```

3. Install the dependencies

```
uv sync
```

3. Create a .env file with the following S3 variables

```
AWS_ENDPOINT_URL=https://[endpoint]
AWS_ACCESS_KEY_ID=[key id]
AWS_SECRET_ACCESS_KEY=[secret key]
```

4. run the builder

```
uv run --env-file .env  python feedbuilder.py
```
