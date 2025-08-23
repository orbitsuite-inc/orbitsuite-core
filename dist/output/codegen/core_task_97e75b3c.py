import tkinter as tk

class Calculator:
    def __init__(self, master):
        self.master = master
        self.master.title("Simple Calculator")

        self.result_var = tk.StringVar()
        self.create_widgets()

    def create_widgets(self):
        entry = tk.Entry(self.master, textvariable=self.result_var, font=('Arial', 24), bd=10, insertwidth=2, width=14, borderwidth=4)
        entry.grid(row=0, column=0, columnspan=4)

        buttons = [
            '7', '8', '9', '/',
            '4', '5', '6', '*',
            '1', '2', '3', '-',
            '0', '.', '=', '+'
        ]

        row_val = 1
        col_val = 0
        for button in buttons:
            action = self.calculate if button == '=' else lambda x=button: self.result_var.set(self.result_var.get() + x)
            tk.Button(self.master, text=button, padx=20, pady=20, font=('Arial', 18), command=action).grid(row=row_val, column=col_val)
            col_val += 1
            if col_val > 3:
                col_val = 0
                row_val += 1

        tk.Button(self.master, text='C', padx=20, pady=20, font=('Arial', 18), command=self.clear).grid(row=row_val, column=0)

    def calculate(self):
        try:
            result = eval(self.result_var.get())
            self.result_var.set(result)
        except Exception:
            self.result_var.set("Error")

    def clear(self):
        self.result_var.set("")

if __name__ == "__main__":
    root = tk.Tk()
    calculator = Calculator(root)
    root.mainloop()