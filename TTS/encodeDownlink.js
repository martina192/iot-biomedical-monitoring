function encodeDownlink(input) {
  var bytes = [];
  var cmd = input.data.command;
  var code;

  if (cmd === "BUZZ_ON")      code = 0x00
  else if (cmd === "BUZZ_OFF")  code = 0x01
  else if (cmd === "LED_ON")  code = 0x10
  else if (cmd === "LED_OFF")   code = 0x11

  bytes[0] = code;

  return {
    bytes: bytes,
    fPort: 1,
    warnings: [],
    errors: []
  };
}