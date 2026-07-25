# SCADA security

The operator runtime defaults to viewer and loopback rsmicro-tagd, never rsm-node. Role names are policy, not authentication. RSM Link and the local API are unencrypted and intended for trusted loopback use. Declarative actions are allow-listed; arbitrary Python, JavaScript and shell execution are prohibited. HMI momentary controls are not hardware safety controls.
