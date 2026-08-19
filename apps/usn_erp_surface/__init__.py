# -*- coding: utf-8 -*-
"""USN ERP Operator Surface — a local app that drives the sovereign node.

The node is the ERP. This package only drives it: `node_binding` is the sole module that touches
`sovereign_agent`, and `server` is a loopback-only Flask shell over it. Neither keeps a store.
"""
__all__ = ["node_binding", "server"]
