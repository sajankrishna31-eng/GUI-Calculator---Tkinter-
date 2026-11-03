"""A keyboard-friendly scientific calculator built with Tkinter."""

from __future__ import annotations

import ast
import math
import operator
import re
import tkinter as tk
from collections.abc import Callable

BACKGROUND = "#101827"
PANEL = "#182336"
DISPLAY = "#0b1220"
TEXT = "#eef3fb"
MUTED = "#91a0b7"
ACCENT = "#51c4a0"
BUTTON = "#223149"
BUTTON_HOVER = "#30445f"
OPERATOR = "#293d59"
ERROR = "#ff8b8b"


def _checked_number(value: object) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("This operation did not produce a real number.")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("The result is outside the calculator's supported range.")
    if isinstance(value, int) and value.bit_length() > 4096:
        raise ValueError("The result is too large.")
    return value


def evaluate_expression(expression: str, angle_mode: str = "DEG") -> int | float:
    """Evaluate a math expression using only explicitly supported operations."""
    if angle_mode not in {"DEG", "RAD"}:
        raise ValueError("Angle mode must be DEG or RAD.")

    normalized = expression.replace("×", "*").replace("÷", "/").replace("−", "-")
    normalized = normalized.replace("^", "**")
    tree = ast.parse(normalized, mode="eval")

    def to_radians(value: float) -> float:
        return math.radians(value) if angle_mode == "DEG" else value

    def from_radians(value: float) -> float:
        return math.degrees(value) if angle_mode == "DEG" else value

    functions = {
        "sin": lambda value: math.sin(to_radians(value)),
        "cos": lambda value: math.cos(to_radians(value)),
        "tan": lambda value: math.tan(to_radians(value)),
        "asin": lambda value: from_radians(math.asin(value)),
        "acos": lambda value: from_radians(math.acos(value)),
        "atan": lambda value: from_radians(math.atan(value)),
        "sqrt": math.sqrt,
        "log": math.log10,
        "ln": math.log,
        "abs": abs,
        "exp": math.exp,
        "factorial": math.factorial,
    }

    binary_operators = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
    }
    unary_operators = {ast.UAdd: operator.pos, ast.USub: operator.neg}

    def visit(node: ast.AST) -> int | float:
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return _checked_number(node.value)
        if isinstance(node, ast.Name):
            constants = {"pi": math.pi, "e": math.e}
            if node.id in constants:
                return constants[node.id]
            raise ValueError(f"Unknown value: {node.id}")
        if isinstance(node, ast.BinOp):
            if isinstance(node.op, ast.Pow):
                base = visit(node.left)
                exponent = visit(node.right)
                if abs(exponent) > 1000:
                    raise ValueError("The exponent is too large.")
                return _checked_number(operator.pow(base, exponent))
            operation = binary_operators.get(type(node.op))
            if operation is None:
                raise ValueError("That operator is not supported.")
            return _checked_number(operation(visit(node.left), visit(node.right)))
        if isinstance(node, ast.UnaryOp):
            operation = unary_operators.get(type(node.op))
            if operation is None:
                raise ValueError("That operator is not supported.")
            return _checked_number(operation(visit(node.operand)))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            function = functions.get(node.func.id)
            if function is None:
                raise ValueError(f"Unknown function: {node.func.id}")
            if node.keywords or len(node.args) != 1:
                raise ValueError(f"{node.func.id} expects one argument.")
            argument = visit(node.args[0])
            if node.func.id == "factorial":
                if not isinstance(argument, int) or not 0 <= argument <= 170:
                    raise ValueError("Factorial requires a whole number from 0 to 170.")
            return _checked_number(function(argument))
        raise ValueError("That expression is not supported.")

    return visit(tree)


class CalculatorApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Scientific Calculator")
        self.root.geometry("940x640")
        self.root.minsize(760, 560)
        self.root.configure(bg=BACKGROUND)
        self.expression = tk.StringVar()
        self.status = tk.StringVar(value="Ready")
        self.angle_mode = "DEG"
        self.just_evaluated = False
        self._build_ui()
        self.display.bind("<Return>", self._on_enter)
        self.display.bind("<KP_Enter>", self._on_enter)
        self.display.bind("<Escape>", self._on_escape)

    def _build_ui(self) -> None:
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=0)
        self.root.grid_rowconfigure(0, weight=1)
        calculator = tk.Frame(self.root, bg=BACKGROUND, padx=24, pady=20)
        calculator.grid(row=0, column=0, sticky="nsew")
        calculator.grid_columnconfigure(0, weight=1)
        calculator.grid_rowconfigure(2, weight=1)

        header = tk.Frame(calculator, bg=BACKGROUND)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 16))
        tk.Label(
            header,
            text="SCIENTIFIC CALCULATOR",
            bg=BACKGROUND,
            fg=TEXT,
            font=("Segoe UI", 15, "bold"),
        ).pack(side="left")
        self.angle_button = self._make_button(
            header, "DEG", self._toggle_angle, style="utility", width=5
        )
        self.angle_button.pack(side="right")

        display_frame = tk.Frame(calculator, bg=DISPLAY, padx=16, pady=12)
        display_frame.grid(row=1, column=0, sticky="ew", pady=(0, 16))
        display_frame.grid_columnconfigure(0, weight=1)
        self.display = tk.Entry(
            display_frame,
            textvariable=self.expression,
            bg=DISPLAY,
            fg=TEXT,
            insertbackground=ACCENT,
            selectbackground="#355575",
            relief="flat",
            justify="right",
            font=("Segoe UI", 27),
            borderwidth=0,
        )
        self.display.grid(row=0, column=0, sticky="ew", ipady=7)
        self.display.focus_set()
        tk.Label(
            display_frame,
            textvariable=self.status,
            bg=DISPLAY,
            fg=MUTED,
            anchor="e",
            font=("Segoe UI", 9),
        ).grid(row=1, column=0, sticky="ew", pady=(5, 0))

        keypad = tk.Frame(calculator, bg=BACKGROUND)
        keypad.grid(row=2, column=0, sticky="nsew")
        for column in range(5):
            keypad.grid_columnconfigure(column, weight=1, uniform="key")
        for row in range(7):
            keypad.grid_rowconfigure(row, weight=1, uniform="key")

        keys = [
            [("sin", "sin("), ("cos", "cos("), ("tan", "tan("), ("√", "sqrt("), ("x²", "^2")],
            [("log", "log("), ("ln", "ln("), ("π", "pi"), ("e", "e"), ("1/x", "1/(")],
            [("(", "("), (")", ")"), ("%", "%"), ("AC", "clear"), ("⌫", "back")],
            [("7", "7"), ("8", "8"), ("9", "9"), ("÷", "÷"), ("×", "×")],
            [("4", "4"), ("5", "5"), ("6", "6"), ("−", "−"), ("+", "+")],
            [("1", "1"), ("2", "2"), ("3", "3"), ("±", "sign"), ("=", "equals")],
            [("0", "0"), (".", "."), ("xʸ", "^"), ("n!", "factorial"), ("", "empty")],
        ]

        for row, keys_in_row in enumerate(keys):
            for column, (label, action) in enumerate(keys_in_row):
                if action == "empty":
                    continue
                style = "number"
                if action in {"clear", "back", "sign"}:
                    style = "utility"
                elif action == "equals":
                    style = "equals"
                elif label in {"÷", "×", "−", "+"}:
                    style = "operator"
                button = self._make_button(
                    keypad, label, lambda item=action: self._press(item), style=style
                )
                if row == 6 and column == 0:
                    button.grid(row=row, column=column, columnspan=2, sticky="nsew", padx=4, pady=4)
                elif row == 6 and column == 1:
                    continue
                else:
                    button.grid(row=row, column=column, sticky="nsew", padx=4, pady=4)

        history_panel = tk.Frame(self.root, bg=PANEL, width=260, padx=16, pady=20)
        history_panel.grid(row=0, column=1, sticky="nsew")
        history_panel.grid_propagate(False)
        history_panel.grid_rowconfigure(1, weight=1)
        tk.Label(
            history_panel,
            text="HISTORY",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI", 12, "bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", pady=(0, 12))
        self.history = tk.Listbox(
            history_panel,
            bg=PANEL,
            fg=MUTED,
            selectbackground="#30445f",
            selectforeground=TEXT,
            relief="flat",
            highlightthickness=0,
            activestyle="none",
            font=("Segoe UI", 10),
            exportselection=False,
        )
        self.history.grid(row=1, column=0, sticky="nsew")
        self.history.bind("<<ListboxSelect>>", self._restore_history)
        self._make_button(
            history_panel, "Clear history", self._clear_history, style="utility"
        ).grid(row=2, column=0, sticky="ew", pady=(12, 0))
        tk.Label(
            history_panel,
            text="Enter: calculate   Esc: clear",
            bg=PANEL,
            fg=MUTED,
            font=("Segoe UI", 8),
            anchor="w",
        ).grid(row=3, column=0, sticky="ew", pady=(14, 0))

    def _make_button(
        self,
        parent: tk.Misc,
        label: str,
        command: Callable[[], None],
        style: str,
        width: int | None = None,
    ) -> tk.Button:
        colors = {
            "number": (BUTTON, TEXT),
            "operator": (OPERATOR, TEXT),
            "utility": ("#34435a", TEXT),
            "equals": (ACCENT, "#0b241e"),
        }
        background, foreground = colors[style]
        button = tk.Button(
            parent,
            text=label,
            command=command,
            bg=background,
            fg=foreground,
            activebackground=BUTTON_HOVER,
            activeforeground=TEXT,
            relief="flat",
            borderwidth=0,
            font=("Segoe UI", 11, "bold"),
            cursor="hand2",
            width=width,
            takefocus=False,
        )
        if width is None:
            button.bind("<Enter>", lambda _event, item=button: item.configure(bg=BUTTON_HOVER))
            button.bind("<Leave>", lambda _event, item=button, color=background: item.configure(bg=color))
        return button

    def _press(self, action: str) -> None:
        if action == "clear":
            self._clear()
        elif action == "back":
            self._backspace()
        elif action == "equals":
            self._calculate()
        elif action == "sign":
            self._toggle_sign()
        elif action == "factorial":
            self._append("factorial(")
        else:
            self._append(action)

    def _append(self, text: str) -> None:
        if self.just_evaluated:
            if text in {"+", "−", "×", "÷", "%", "^", "^2", ")"}:
                pass
            else:
                self.expression.set("")
        self.just_evaluated = False
        self.expression.set(self.expression.get() + text)
        self.status.set("Ready")
        self.display.icursor(tk.END)

    def _backspace(self) -> None:
        current = self.expression.get()
        if self.just_evaluated:
            self._clear()
            return
        if current:
            self.expression.set(current[:-1])
        self.status.set("Ready")
        self.display.icursor(tk.END)

    def _clear(self) -> None:
        self.expression.set("")
        self.status.set("Ready")
        self.just_evaluated = False

    def _toggle_sign(self) -> None:
        current = self.expression.get().rstrip()
        if not current:
            self._append("−")
            return
        if self.just_evaluated:
            self.expression.set(f"-({current})")
            self.just_evaluated = False
            return
        match = re.search(r"(?<![\w)])(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?$", current)
        if match:
            number = match.group()
            prefix = current[: match.start()]
            self.expression.set(prefix + (number[1:] if number.startswith("-") else "−" + number))
        else:
            self.expression.set(f"−({current})")
        self.display.icursor(tk.END)

    def _toggle_angle(self) -> None:
        self.angle_mode = "RAD" if self.angle_mode == "DEG" else "DEG"
        self.angle_button.configure(text=self.angle_mode)
        self.status.set(f"Angle mode: {self.angle_mode}")

    def _calculate(self) -> None:
        expression = self.expression.get().strip()
        if not expression:
            return
        try:
            result = evaluate_expression(expression, self.angle_mode)
        except (SyntaxError, ValueError, TypeError, ZeroDivisionError, OverflowError) as error:
            message = str(error) or "Check the expression and try again."
            self.status.set(message[:65])
            self.display.configure(fg=ERROR)
            self.root.after(1200, lambda: self.display.configure(fg=TEXT))
            self.just_evaluated = False
            return
        self.history.insert(0, f"{expression} = {self._format_result(result)}")
        self.expression.set(self._format_result(result))
        self.status.set("Result")
        self.just_evaluated = True
        self.display.icursor(tk.END)

    @staticmethod
    def _format_result(result: int | float) -> str:
        if isinstance(result, int):
            return str(result)
        if result.is_integer() and abs(result) < 1e15:
            return str(int(result))
        return f"{result:.12g}"

    def _clear_history(self) -> None:
        self.history.delete(0, tk.END)

    def _restore_history(self, _event: tk.Event) -> None:
        selection = self.history.curselection()
        if selection:
            item = self.history.get(selection[0])
            self.expression.set(item.split(" = ", 1)[-1])
            self.status.set("Restored result")
            self.just_evaluated = True

    def _on_enter(self, _event: tk.Event) -> str:
        self._calculate()
        return "break"

    def _on_escape(self, _event: tk.Event) -> str:
        self._clear()
        return "break"


def main() -> None:
    root = tk.Tk()
    CalculatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
