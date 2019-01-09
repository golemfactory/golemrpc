Tests assume that there is a localhost golem node available for computation and that `cli_secret` and `rpc_cert` are from this node's datadir: `$home/Projects/golem/node_A`. Fix this accordingly to your setup in `utils.py` where the rpc component factory function resides. When you are done, run:

```python
python -m pytest tests/
```
