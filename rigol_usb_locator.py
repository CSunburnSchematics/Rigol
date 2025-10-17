#!/usr/bin/env python3
"""
USB-only Rigol instrument locator + initializer.

- Discovers USB VISA resources
- Identifies devices via *IDN?
- Initializes custom classes:
    RigolPowerSupply, RigolLoad, RigolOscilloscope
- Exposes getters that return ready instances or None if not found
"""

from __future__ import annotations
import pyvisa
from typing import Optional, Dict, Tuple

# --- Your custom classes (adjust module paths if needed) ---
from Rigol_DP832A import RigolPowerSupply
from Rigol_DL3021A import RigolLoad
from Rigol_DS1054z import RigolOscilloscope

# Choose backend: "" = default (NI-VISA if present), "@py" = pyvisa-py
DEFAULT_BACKEND = ""   # set to "@py" if you don’t use NI-VISA


class RigolUsbLocator:
    """Scans VISA (USB only), initializes custom classes, and caches instances."""
    # Simple IDN heuristics; extend as needed
    MATCHERS: Dict[str, Tuple[str, ...]] = {
        "oscilloscope": ("DS1202Z-E", "DS1Z", "MSO", "RIGOL,DS"),  # Z-series etc.
        "power_supply": ("DP832A", "DP8", "RIGOL,DP"),
        "load":         ("DL3021A", "DL3", "RIGOL,DL"),
    }

    def __init__(self, backend: str = DEFAULT_BACKEND, verbose: bool = True):
        self.verbose = verbose
        self.rm = pyvisa.ResourceManager(backend) if backend else pyvisa.ResourceManager()
        self._osc: Optional[RigolOscilloscope] = None
        self._psu: Optional[RigolPowerSupply] = None
        self._load: Optional[RigolLoad] = None
        self._ids: Dict[str, str] = {}   # addr -> IDN cache

    # -------- public API --------
    def refresh(self) -> None:
        """Rescan USB devices, (re)initialize first matching osc/psu/load."""
        if self.verbose:
            print(f"[locator] Backend: {self.rm}")

        # Reset caches
        self._osc = self._psu = self._load = None
        self._ids.clear()

        addrs = self._list_usb_resources()
        if self.verbose:
            print(f"[locator] USB resources: {addrs}")

        # Probe *IDN? and classify
        for addr in addrs:
            idn = self._query_idn(addr)
            if not idn:
                if self.verbose:
                    print(f"[locator] {addr}: no IDN")
                continue

            role = self._classify(idn)
            if self.verbose:
                print(f"[locator] {addr}: {idn}  ->  {role or 'unknown'}")

            try:
                if role == "oscilloscope" and self._osc is None:
                    self._osc = RigolOscilloscope(addr)
                elif role == "power_supply" and self._psu is None:
                    self._psu = RigolPowerSupply(addr)
                elif role == "load" and self._load is None:
                    self._load = RigolLoad(addr)
            except Exception as e:
                if self.verbose:
                    print(f"[locator] init failed for {role or 'unknown'} at {addr}: {e}")

        # Optional: quick connectivity check (safe, non-fatal)
        for name, obj in (("oscilloscope", self._osc),
                          ("power supply", self._psu),
                          ("electronic load", self._load)):
            if obj is None:
                if self.verbose:
                    print(f"[locator] {name}: NOT FOUND")
                continue
            try:
                ok = obj.check_connection()
                if self.verbose:
                    print(f"[locator] {name}: {'OK' if ok else 'FAILED check_connection()'}")
            except Exception as e:
                if self.verbose:
                    print(f"[locator] {name}: check_connection error: {e}")

    def get_oscilloscope(self) -> Optional[RigolOscilloscope]:
        return self._osc

    def get_power_supply(self) -> Optional[RigolPowerSupply]:
        return self._psu

    def get_load(self) -> Optional[RigolLoad]:
        return self._load

    def list_found(self) -> Dict[str, Optional[str]]:
        """Return a friendly summary of what we’ve got (IDN strings if available)."""
        def idn_of(obj):
            try:
                return obj.instrument.query("*IDN?").strip() if obj else None
            except Exception:
                return None
        return {
            "oscilloscope": idn_of(self._osc),
            "power_supply": idn_of(self._psu),
            "load":         idn_of(self._load),
        }

    # -------- internals --------
    def _list_usb_resources(self):
        try:
            all_res = self.rm.list_resources()
        except Exception as e:
            if self.verbose: print(f"[locator] list_resources failed: {e}")
            return ()
        # Keep only USB endpoints (ignore ASRL/LAN for now)
        return tuple(a for a in all_res if a.upper().startswith("USB"))

    def _query_idn(self, addr: str, timeout_ms: int = 1500) -> Optional[str]:
        if addr in self._ids:
            return self._ids[addr]
        try:
            inst = self.rm.open_resource(addr)
            inst.timeout = timeout_ms
            idn = inst.query("*IDN?").strip()
            try: inst.close()
            except Exception: pass
            self._ids[addr] = idn
            return idn
        except Exception:
            self._ids[addr] = None  # remember the failure
            return None

    def _classify(self, idn: str) -> Optional[str]:
        up = idn.upper()
        for role, keys in self.MATCHERS.items():
            if any(k.upper() in up for k in keys):
                return role
        return None


# ---- Optional CLI demo ----
if __name__ == "__main__":
    loc = RigolUsbLocator(backend=DEFAULT_BACKEND, verbose=True)
    loc.refresh()

    print("\n== Status ==")
    found = loc.list_found()
    print(f"all usb resources: ", loc._list_usb_resources())
    print(f"Oscilloscope  : {found['oscilloscope'] or 'NOT FOUND'}")
    print(f"Power Supply  : {found['power_supply'] or 'NOT FOUND'}")
    print(f"Electronic Load: {found['load'] or 'NOT FOUND'}")

    # Example: use the objects if present
    osc = loc.get_oscilloscope()
    psu = loc.get_power_supply()
    eload = loc.get_load()

    if osc:
        try:
            print("[demo] Scope IDN:", osc.instrument.query("*IDN?").strip())
        except Exception as e:
            print("[demo] Scope query failed:", e)
    if psu:
        try:
            print("[demo] PSU IDN  :", psu.instrument.query("*IDN?").strip())
        except Exception as e:
            print("[demo] PSU query failed:", e)
    if eload:
        try:
            print("[demo] Load IDN :", eload.instrument.query("*IDN?").strip())
        except Exception as e:
            print("[demo] Load query failed:", e)
