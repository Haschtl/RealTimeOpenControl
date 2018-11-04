#!/usr/bin/python
class MultimeterMessage:
    MESSAGE_LENGTH=14

    @classmethod
    def check_first_byte(cls,byte):
        return byte == 0x2d or byte == 0x2b

    def __init__(self, message_bytes):
        """
        :param bytes message_bytes: Raw message
        """
        self.raw_message = message_bytes
        self._parse()

    def __str__(self):
        """
        Return reading and warning flags
        """
        measurement_str = self.get_reading()
        hold = "[HOLD]" if self.hold else ""
        bat = "[BATTERY_LOW]" if self.batlow else ""
        rel = "[RELATIVE]" if self.rel else ""
        warnings_str = hold+bat+rel
        return measurement_str+" "+warnings_str

    def __repr__(self):
        return("MultimeterMessage(message_bytes="+repr(self.raw_message)+")")

    def get_reading(self):
        """
        Return reading as shown on the Multimeter
        """
        measurement_str = self.number+self.unit+" "+self.mode
        return measurement_str

    def get_base_reading(self):
        """
        Return reading converted to the base unit
        """
        return str(self.value * self.multiplier) + self.base_unit + " " + self.mode

    def _parse(self):
        raw = self.raw_message

        #read flags
        self.bg_active  = _read_bit(raw[7], 0)
        self.hold       = _read_bit(raw[7], 1)
        self.rel        = _read_bit(raw[7], 2)
        self.ac         = _read_bit(raw[7], 3)
        self.dc         = _read_bit(raw[7], 4)
        self.auto       = _read_bit(raw[7], 5)

        self.nano       = _read_bit(raw[8], 1)
        self.batlow     = _read_bit(raw[8], 2)
        self.min        = _read_bit(raw[8], 4)
        self.max        = _read_bit(raw[8], 5)

        self.percent    = _read_bit(raw[9], 1)
        self.diode      = _read_bit(raw[9], 2)
        self.sound      = _read_bit(raw[9], 3)
        self.mega       = _read_bit(raw[9], 4)
        self.kilo       = _read_bit(raw[9], 5)
        self.milli      = _read_bit(raw[9], 6)
        self.micro      = _read_bit(raw[9], 7)

        self.fahrenheit = _read_bit(raw[10], 0)
        self.celsius    = _read_bit(raw[10], 1)
        self.farad      = _read_bit(raw[10], 2)
        self.hertz      = _read_bit(raw[10], 3)
        self.ohm        = _read_bit(raw[10], 5)
        self.amp        = _read_bit(raw[10], 6)
        self.volt       = _read_bit(raw[10], 7)

        if self.dc:
            self.mode = "DC"
        elif self.ac:
            self.mode = "AC"
        else:
            self.mode = "" #Happens when measuring resistance, capacitance, ...

        self.bg_value = int(raw[11])-128 if _read_bit(raw[11], 7) else int(raw[11]) #convert unsigned byte to signed

        self._set_unit()
        self.number = self._get_number() #str
        self.value = float(self.number)
        self.base_value = self.value * self.multiplier


    def _get_number(self):
        """
        Return String of the number displayed on Multimeter
        """
        raw = self.raw_message
        minus = chr(raw[0])
        digit1 = chr(raw[1])
        digit2 = chr(raw[2])
        digit3 = chr(raw[3])
        digit4 = chr(raw[4])

        point_position = int(chr(raw[6]))

        point1 = ""
        point2 = ""
        point3 = ""

        if point_position == 1:
            point1 = "."
        elif point_position == 2:
            point2 = "."
        elif point_position == 4:
            point3 = "."
        
        if digit2 == "0" and digit3 == ":" and digit1 == "?" and digit4 == "?":
            raise ValueError("Overload")

        return minus+digit1+point1+digit2+point2+digit3+point3+digit4

    def _set_unit(self):
        """
        Sets self.multiplier, self.unit and self.base_unit
        """
        modifier = ""
        if self.kilo:
            modifier = "k"
            self.multiplier = 1000
        elif self.nano:
            modifier = "n"
            self.multiplier = 0.000000001
        elif self.micro:
            self.multiplier = 0.000001
            modifier = "u" #um Probleme mit Zeichenkodierungen zu vermeiden
        elif self.milli:
            modifier = "m"
            self.multiplier = 0.001
        elif self.mega:
            modifier = "M"
            self.multiplier = 1000000
        else:
            self.multiplier = 1
        
        unit = ""
        if self.percent:
            unit = "%"
        elif self.ohm:
            unit = "Ohm" #same as micro
        elif self.farad:
            unit = "F"
        elif self.hertz:
            unit = "Hz"
        elif self.volt:
            unit = "V"
        elif self.amp:
            unit = "A"
        elif self.celsius:
            unit = "°C"
        elif self.fahrenheit:
            unit = "°F"
        else:
            raise ValueError("no unit found")
        
        self.unit = modifier+unit
        self.base_unit = unit

    def get_json(self):
        import json

        mdict =   { "reading": self.get_reading(),
                    "base_reading": self.get_base_reading(),
                    "value": self.value,
                    "unit": self.unit,
                    "mode": self.mode,
                    "battery_low": self.batlow,
                    "hold": self.hold,
                    "relative": self.rel,
                    "autorange": self.auto,
                    "raw_self": self.raw_message.hex(),
                    "bargraph": self.bg_value if self.bg_active else None,
                    "diode_test": self.diode }
        return json.dumps(mdict)

    def get_percent(self):
        in_min = 0
        in_max = 40
        out_min = 0
        out_max = 100
        return (self.bg_value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min

def _read_bit(byte,bitnum):
    return True if (byte&(1<<bitnum)) else False
