class ScadaError(Exception): pass
class ConfigurationError(ScadaError): pass
class RegistryError(ScadaError): pass
class PolicyError(ScadaError): pass
class HistorianError(ScadaError): pass
