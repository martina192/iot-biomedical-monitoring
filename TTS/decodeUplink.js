function decodeUplink(input) {
  
  return {
    data: {
      type: input.bytes[0],
      length: input.bytes[1],
      bpm: input.bytes[2],
      arritimia: input.bytes[3],
    },
    warnings: [],
    errors: []
  };
}