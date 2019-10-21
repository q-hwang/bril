#!/usr/bin/env node
import * as bril from './bril';
import {readStdin, unreachable} from './util';

const argCounts:{[key in bril.OpCode]: number | null} = {
  add: 2,
  mul: 2,
  sub: 2,
  div: 2,
  id: 1,
  lt: 2,
  le: 2,
  gt: 2,
  ge: 2,
  eq: 2,
  not: 2,
  and: 2,
  or: 2,
  print: null,  // Any number of arguments.
  br: 3,
  jmp: 1,
  ret: 0,
  print_grad: null,
};

class RevADNode {
  value: number;
  gradValue: number | undefined = undefined;
  children: [number, RevADNode][] = [];
  constructor(value: number) {
    this.value = value;
  }
  grad(): number {
    if (!this.gradValue) {
      this.gradValue = 0;
      for (const val of this.children) {
        const [num, node] = val;
        this.gradValue += num * node.grad();
      }
    }
    return this.gradValue!;
  }
}
type Env = Map<bril.Ident, [bril.Value, number[]| undefined, RevADNode | undefined]>;
let entry_vars: string[] = [];
let var_grad: bril.Ident[] = []
let num_grad: number = 0

type NumGrad = [number, number[], RevADNode];
function apply(val1:NumGrad, val2:NumGrad, f:(x11:number,x12:number,x21:number,x22:number)=> number): number[] {
  let arr = new Array(num_grad)
  for(let i = 0; i < num_grad; i ++) {
    arr[i] = f(val1[0], val1[1][i], val2[0], val2[1][i])
  }
  return arr
}

function get(env: Env, ident: bril.Ident) {
  let val = env.get(ident);
  if (typeof val === 'undefined') {
    throw `undefined variable ${ident}`;
  }
  return val;
}

/**
 * Ensure that the instruction has exactly `count` arguments,
 * throwing an exception otherwise.
 */
function checkArgs(instr: bril.Operation, count: number) {
  if (instr.args.length != count) {
    throw `${instr.op} takes ${count} argument(s); got ${instr.args.length}`;
  }
}

function getInt(instr: bril.Operation, env: Env, index: number): [number, number[], RevADNode] {
  let val = get(env, instr.args[index]);
  if (typeof val[0] !== 'number' || typeof val[1] === 'undefined') {
    throw `${instr.op} argument ${index} must be a number`;
  }
  // console.log("80: ", instr.args[index]);
  if (!val[2]) {
    return [val[0], val[1], new RevADNode(val[0])];
  } else {
    return [val[0], val[1], val[2]!];
  }
}

function getBool(instr: bril.Operation, env: Env, index: number) {
  let val = get(env, instr.args[index]);
  if (typeof val[0] !== 'boolean') {
    throw `${instr.op} argument ${index} must be a boolean`;
  }
  return val[0];
}

/**
 * The thing to do after interpreting an instruction: either transfer
 * control to a label, go to the next instruction, or end thefunction.
 */
type Action =
  {"label": bril.Ident} |
  {"next": true} |
  {"end": true};
let NEXT: Action = {"next": true};
let END: Action = {"end": true};

/**
 * Interpret an instruction in a given environment, possibly updating the
 * environment. If the instruction branches to a new label, return that label;
 * otherwise, return "next" to indicate that we should proceed to the next
 * instruction or "end" to terminate the function.
 */
function evalInstr(instr: bril.Instruction, env: Env): Action {
  // console.log("110: ", env);
  // Check that we have the right number of arguments.
  if (instr.op !== "const") {
    let count = argCounts[instr.op];
    if (count === undefined) {
      throw "unknown opcode " + instr.op;
    } else if (count !== null) {
      checkArgs(instr, count);
    }
  }

  switch (instr.op) {
  case "const":
    env.set(instr.dest, [instr.value, new Array(num_grad).fill(0), undefined]);
    return NEXT;

  case "id": {
    let val = get(env, instr.args[0]);
    env.set(instr.dest, val);
    return NEXT;
  }

  case "add": {
    let x1 = getInt(instr, env, 0);
    let x2 = getInt(instr, env, 1);
    let newADNode = new RevADNode(x1[0] + x2[0]);
    x1[2].children.push([1.0, newADNode]);
    x2[2].children.push([1.0, newADNode]);
    env.set(instr.dest, [x1[0] + x2[0], apply(x1,x2, (x11,x12,x21,x22) =>  x12 + x22), newADNode]);
    return NEXT;
  }

  case "mul": {
    let x1 = getInt(instr, env, 0);
    let x2 = getInt(instr, env, 1);
    let newADNode = new RevADNode(x1[0] * x2[0]);
    // console.log("146: ", x1, x2);
    x1[2].children.push([x2[0], newADNode]);
    x2[2].children.push([x1[0], newADNode]);
    env.set(instr.dest, [x1[0] * x2[0], apply(x1,x2, (x11,x12,x21,x22) =>  x12 *x21 + x11 *x22), newADNode]);
    return NEXT;
  }

  case "sub": {
    let x1 = getInt(instr, env, 0);
    let x2 = getInt(instr, env, 1);
    let newADNode = new RevADNode(x1[0] - x2[0]);
    x1[2].children.push([-1.0, newADNode]);
    x2[2].children.push([-1.0, newADNode]);
    env.set(instr.dest, [x1[0] - x2[0],  apply(x1,x2, (x11,x12,x21,x22) =>  x12 - x22), newADNode]);
    return NEXT;
  }

  case "div": {
    let x1 = getInt(instr, env, 0);
    let x2 = getInt(instr, env, 1);
    let newADNode = new RevADNode(x1[0] / x2[0]);
    x1[2].children.push([1.0/x2[0], newADNode]);
    x2[2].children.push([-x1[0]/(x2[0]*x2[0]), newADNode]);
    env.set(instr.dest, [x1[0] / x2[0], apply(x1,x2, (x11,x12,x21,x22) =>  (x12 *x21 - x11 *x22)/ x21**2), newADNode]);
    return NEXT;
  }

  case "le": {
    let val = getInt(instr, env, 0)[0] <= getInt(instr, env, 1)[0];
    env.set(instr.dest, [val, undefined, undefined]);
    return NEXT;
  }

  case "lt": {
    let val = getInt(instr, env, 0)[0] < getInt(instr, env, 1)[0];
    env.set(instr.dest, [val, undefined, undefined]);
    return NEXT;
  }

  case "gt": {
    let val = getInt(instr, env, 0)[0] > getInt(instr, env, 1)[0];
    env.set(instr.dest,[val, undefined, undefined]);
    return NEXT;
  }

  case "ge": {
    let val = getInt(instr, env, 0)[0] >= getInt(instr, env, 1)[0];
    env.set(instr.dest, [val, undefined, undefined]);
    return NEXT;
  }

  case "eq": {
    let val = getInt(instr, env, 0)[0] === getInt(instr, env, 1)[0];
    env.set(instr.dest,[val, undefined, undefined]);
    return NEXT;
  }

  case "not": {
    let val = !getBool(instr, env, 0);
    env.set(instr.dest, [val, undefined, undefined]);
    return NEXT;
  }

  case "and": {
    let val = getBool(instr, env, 0) && getBool(instr, env, 1);
    env.set(instr.dest, [val, undefined, undefined]);
    return NEXT;
  }

  case "or": {
    let val = getBool(instr, env, 0) || getBool(instr, env, 1);
    env.set(instr.dest, [val, undefined, undefined]);
    return NEXT;
  }

  case "print": {
    let values = instr.args.map(i => get(env, i)[0]);
    console.log(...values);
    return NEXT;
  }

  case "print_grad": {
    if(instr.args.length < 1) {
      throw "no target var for differentiation";
    }
    // let target = getInt(instr, env, 0)[1]
    // let values = instr.args.slice(1).map(i => target[var_grad.indexOf(i)]);
    // // console.log(env);
    // console.log(...values);

    let target = getInt(instr, env, 0)[2]
    target.gradValue = 1.0;
    let values = [];
    for (let i=0; i<entry_vars.length; i++) {
      const vals = get(env, entry_vars[i]);
      values.push(vals[2]!.grad());
    }
    // console.log(env);
    console.log(...values);

    return NEXT;
  }

  case "jmp": {
    return {"label": instr.args[0]};
  }

  case "br": {
    let cond = getBool(instr, env, 0);
    if (cond) {
      return {"label": instr.args[1]};
    } else {
      return {"label": instr.args[2]};
    }
  }

  case "ret": {
    return END;
  }
  }
  unreachable(instr);
  throw `unhandled opcode ${(instr as any).op}`;
}

function evalFunc(func: bril.Function) {
  let env: Env = new Map();
  var_grad = func.args
  num_grad = func.args.length
  for (let i = 0; i < func.args.length; ++i) {
    let arr = new Array(num_grad).fill(0);
    arr[i] = 1
    env.set(func.args[i], [func.values[i], arr, new RevADNode(func.values[i])]);
    entry_vars.push(func.args[i]);
  }
  for (let i = 0; i < func.instrs.length; ++i) {
    let line = func.instrs[i];
    if ('op' in line) {
      let action = evalInstr(line, env);

      if ('label' in action) {
        // Search for the label and transfer control.
        for (i = 0; i < func.instrs.length; ++i) {
          let sLine = func.instrs[i];
          if ('label' in sLine && sLine.label === action.label) {
            break;
          }
        }
        if (i === func.instrs.length) {
          throw `label ${action.label} not found`;
        }
      } else if ('end' in action) {
        return;
      }
    }
  }
}

function evalProg(prog: bril.Program) {
  for (let func of prog.functions) {
    if (func.name === "main") {
      evalFunc(func);
    }
  }
}

async function main() {
  let prog = JSON.parse(await readStdin()) as bril.Program;
  evalProg(prog);
}

// Make unhandled promise rejections terminate.
process.on('unhandledRejection', e => { throw e });

main();
