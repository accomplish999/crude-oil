/** Browser formulas over sheet columns. Blank input stays blank. No hidden fills. */

export function formatNum(value) {
  if (!Number.isFinite(value)) return "";
  const nearest = Math.round(value);
  if (Math.abs(value - nearest) < 1e-9 && Math.abs(value) < 1e15) return String(nearest);
  for (let digits = 0; digits <= 8; digits += 1) {
    const text = value.toFixed(digits);
    if (Math.abs(Number(text) - value) < 1e-9) return text;
  }
  return value.toPrecision(8);
}

export function evaluateFormula(expression, row, prev = {}) {
  const text = String(expression ?? "").trim();
  if (!text) throw new Error("Empty formula.");
  const parser = new Parser(text, row, prev);
  const value = parser.parseExpression();
  parser.skip();
  if (parser.pos !== parser.text.length) throw new Error("Could not read the rest of the formula.");
  if (value == null) return "";
  return formatNum(value);
}

class Parser {
  constructor(text, row, prev) {
    this.text = text;
    this.row = row;
    this.prev = prev;
    this.pos = 0;
  }

  parseExpression() {
    let value = this.parseTerm();
    while (true) {
      this.skip();
      const op = this.peek();
      if (op !== "+" && op !== "-") break;
      this.pos += 1;
      const right = this.parseTerm();
      if (value == null || right == null) return null;
      value = op === "+" ? value + right : value - right;
    }
    return value;
  }

  parseTerm() {
    let value = this.parseFactor();
    while (true) {
      this.skip();
      const op = this.peek();
      if (op !== "*" && op !== "/") break;
      this.pos += 1;
      const right = this.parseFactor();
      if (value == null || right == null) return null;
      if (op === "/" && right === 0) return null;
      value = op === "*" ? value * right : value / right;
    }
    return value;
  }

  parseFactor() {
    this.skip();
    const op = this.peek();
    if (op === "+" || op === "-") {
      this.pos += 1;
      const value = this.parseFactor();
      if (value == null) return null;
      return op === "-" ? -value : value;
    }
    if (op === "(") {
      this.pos += 1;
      const value = this.parseExpression();
      this.skip();
      if (this.peek() !== ")") throw new Error("Missing parenthesis.");
      this.pos += 1;
      return value;
    }
    if (this.isIdentStart()) return this.parseIdentOrCall();
    if (this.isDigit() || op === ".") return this.parseNumber();
    throw new Error("Unexpected formula input.");
  }

  parseIdentOrCall() {
    const name = this.parseIdent();
    this.skip();
    if (this.peek() !== "(") return this.cell(name, this.row);
    this.pos += 1;
    const upper = name.toUpperCase();
    if (upper === "LAG") {
      this.skip();
      const inner = this.parseIdent();
      this.skip();
      if (this.peek() !== ")") throw new Error("LAG takes one column.");
      this.pos += 1;
      return this.cell(inner, this.prev);
    }
    if (upper !== "LOG" && upper !== "ABS") throw new Error("Unknown function.");
    const inner = this.parseExpression();
    this.skip();
    if (this.peek() !== ")") throw new Error("Missing parenthesis.");
    this.pos += 1;
    if (inner == null) return null;
    if (upper === "ABS") return Math.abs(inner);
    if (inner <= 0) return null;
    return Math.log(inner);
  }

  cell(name, source) {
    if (!source || !Object.prototype.hasOwnProperty.call(source, name)) {
      throw new Error(`No column ${name}.`);
    }
    const raw = source[name];
    if (raw == null || raw === "") return null;
    const value = Number(raw);
    if (!Number.isFinite(value)) return null;
    return value;
  }

  parseIdent() {
    const start = this.pos;
    if (!this.isIdentStart()) throw new Error("Expected a column.");
    this.pos += 1;
    while (this.isIdentPart()) this.pos += 1;
    return this.text.slice(start, this.pos);
  }

  parseNumber() {
    const start = this.pos;
    while (this.isDigit()) this.pos += 1;
    if (this.peek() === ".") {
      this.pos += 1;
      while (this.isDigit()) this.pos += 1;
    }
    const value = Number(this.text.slice(start, this.pos));
    if (!Number.isFinite(value)) throw new Error("Bad number.");
    return value;
  }

  skip() {
    while (this.peek() === " ") this.pos += 1;
  }

  peek() {
    return this.text[this.pos] ?? "";
  }

  isDigit() {
    const code = this.text.charCodeAt(this.pos);
    return code >= 48 && code <= 57;
  }

  isIdentStart() {
    const code = this.text.charCodeAt(this.pos);
    return (code >= 65 && code <= 90) || (code >= 97 && code <= 122);
  }

  isIdentPart() {
    const code = this.text.charCodeAt(this.pos);
    return this.isIdentStart() || (code >= 48 && code <= 57) || this.peek() === "_";
  }
}
