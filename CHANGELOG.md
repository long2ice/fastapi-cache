# ChangeLog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This project uses [*towncrier*](https://towncrier.readthedocs.io/) and the changes for the upcoming release can be found in <https://github.com/long2ice/fastapi-cache/tree/main/changelog.d/>.

<!-- towncrier release notes start -->

## [0.2.2](https://github.com/long2ice/fastapi-cache/tree/0.2.2) - 2025-01-18

### Bug Fixes

- Fix failing tests (#459) [#459](https://github.com/long2ice/fastapi-cache/issues/459)

### Build Changes

- Use `importlib.metadata` to include project version string as `fastapi_cache.__version__`. [#172](https://github.com/long2ice/fastapi-cache/issues/172)
- (dependabot) Bump actions/checkout from 2 to 4 [#293](https://github.com/long2ice/fastapi-cache/issues/293)
- (dependabot) Bump actions/download-artifact from 2 to 4 (#359) [#359](https://github.com/long2ice/fastapi-cache/issues/359)
- (dependabot) Bump actions/upload-artifact from 3 to 4 (#360) [#360](https://github.com/long2ice/fastapi-cache/issues/360)
- (dependabot) Bump actions/cache from 3 to 4 (#378) [#378](https://github.com/long2ice/fastapi-cache/issues/378)
- (dependabot) Bump dependabot/fetch-metadata from 1 to 2 (#464) [#464](https://github.com/long2ice/fastapi-cache/issues/464)
- (dependabot) Bump tox from 4.20.0 to 4.23.2 (#466) [#466](https://github.com/long2ice/fastapi-cache/issues/466)
- (dependabot) Bump fastapi from 0.115.0 to 0.115.6 (#486) [#486](https://github.com/long2ice/fastapi-cache/issues/486)
- (dependabot) Bump redis from 5.0.8 to 5.2.1 (#490) [#490](https://github.com/long2ice/fastapi-cache/issues/490)
- (dependabot) Bump uvicorn from 0.30.6 to 0.33.0 (#493) [#493](https://github.com/long2ice/fastapi-cache/issues/493)
- (dependabot) Bump pyright from 1.1.381 to 1.1.392.post0 (#507) [#507](https://github.com/long2ice/fastapi-cache/issues/507)
- (dependabot) Bump towncrier from 22.12.0 to 24.8.0 (#509) [#509](https://github.com/long2ice/fastapi-cache/issues/509)

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
