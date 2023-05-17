# ChangeLog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This project uses [*towncrier*](https://towncrier.readthedocs.io/) and the changes for the upcoming release can be found in <https://github.com/long2ice/fastapi-cache/tree/main/changelog.d/>.

<!-- towncrier release notes start -->

## 0.2

### 0.2.1
- Fix picklecoder
- Fix connection failure transparency and add logging
- Add Cache-Control and ETag on first response
- Support Async RedisCluster client from redis-py

### 0.2.0

- Make `request` and `response` optional.
- Add typing info to the `cache` decorator.
- Support cache jinja2 template response.
- Support cache `JSONResponse`
- Add `py.typed` file and type hints
- Add TestCase
- Fix cache decorate sync function
- Transparently handle backend connection failures.

## 0.1

### 0.1.10

- Add `Cache-Control:no-cache` support.

### 0.1.9

- Replace `aioredis` with `redis-py`.

### 0.1.8

- Support `dynamodb` backend.

### 0.1.7

- Fix default json coder for datetime.
- Add `enable` param to `init`.

### 0.1.6

- Fix redis cache.
- Encode key builder.

### 0.1.5

- Fix setting expire for redis (#24)
- Update expire key

### 0.1.4

- Fix default expire for memcached. (#13)
- Update default key builder. (#12)

### 0.1.3

- Fix cache key builder.

### 0.1.2

- Add default config when init.
- Update JsonEncoder.

### 0.1.1

- Add in-memory support.

### 0.1.0

- First version release.
