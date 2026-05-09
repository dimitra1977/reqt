import tkinter as tk
from tkinter import ttk, messagebox
from requirements_db import RequirementDatabase

LEVEL_LABELS = {
    0: 'Feature',
    1: 'User Story',
    2: 'System Requirement',
    3: 'Sub-System / Interface Requirement',
    4: 'Software / Hardware Requirement',
}


class RequirementsApp:
    def __init__(self):
        self.db = RequirementDatabase('requirements.db')
        self.selected_id = None

        self.root = tk.Tk()
        self.root.title('Requirements Browser')
        self.root.geometry('1100x640')

        self.build_ui()
        self.refresh_tree()

    def build_ui(self):
        search_frame = ttk.Frame(self.root, padding=(12, 12, 12, 6))
        search_frame.pack(fill='x')

        ttk.Label(search_frame, text='Search:').pack(side='left')
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side='left', fill='x', expand=True, padx=(8, 8))
        self.search_entry.bind('<Return>', lambda event: self.refresh_tree())

        ttk.Button(search_frame, text='Search', command=self.refresh_tree).pack(side='left')
        ttk.Button(search_frame, text='Clear', command=self.clear_search).pack(side='left', padx=(8, 0))

        main_frame = ttk.Frame(self.root, padding=(12, 0, 12, 12))
        main_frame.pack(fill='both', expand=True)

        tree_frame = ttk.Frame(main_frame)
        tree_frame.pack(fill='both', expand=True, side='left')

        self.tree = ttk.Treeview(tree_frame, columns=('level', 'summary'), show='tree headings', selectmode='browse')
        self.tree.heading('#0', text='Requirement')
        self.tree.heading('level', text='Level')
        self.tree.heading('summary', text='Summary')
        self.tree.column('level', width=140, anchor='center')
        self.tree.column('summary', width=320, anchor='w')
        self.tree.pack(fill='both', expand=True, side='left')
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)

        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree.yview)
        scrollbar.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=scrollbar.set)

        detail_frame = ttk.Frame(main_frame)
        detail_frame.pack(fill='both', expand=True, side='right')

        fields = [
            ('Summary', 'summary'),
            ('Description', 'description'),
            ('Level', 'level'),
            ('Parent', 'parent'),
            ('Custom Field 1', 'custom_field_1'),
            ('Custom Field 2', 'custom_field_2'),
            ('Custom Field 3', 'custom_field_3'),
            ('Custom Field 4', 'custom_field_4'),
        ]

        self.widgets = {}
        for label_text, field_name in fields:
            frame = ttk.Frame(detail_frame, padding=(0, 4, 0, 4))
            frame.pack(fill='x')
            ttk.Label(frame, text=label_text + ':', width=16, anchor='w').pack(side='left')

            if field_name == 'description':
                widget = tk.Text(frame, height=6, wrap='word')
                widget.pack(fill='both', expand=True)
            elif field_name == 'level':
                widget = ttk.Combobox(frame, values=list(LEVEL_LABELS.keys()), state='readonly')
                widget.pack(fill='x', expand=True)
            elif field_name == 'parent':
                widget = ttk.Combobox(frame, state='readonly')
                widget.pack(fill='x', expand=True)
            else:
                widget = ttk.Entry(frame)
                widget.pack(fill='x', expand=True)

            self.widgets[field_name] = widget

        actions = ttk.Frame(detail_frame, padding=(0, 10, 0, 0))
        actions.pack(fill='x')

        ttk.Button(actions, text='New Root Requirement', command=self.create_root_requirement).pack(side='left')
        ttk.Button(actions, text='New Child Requirement', command=self.create_child_requirement).pack(side='left', padx=(8, 0))
        ttk.Button(actions, text='Save', command=self.save_changes).pack(side='left', padx=(8, 0))
        ttk.Button(actions, text='Delete', command=self.delete_requirement).pack(side='left', padx=(8, 0))

        self.status_label = ttk.Label(self.root, text='Ready', anchor='w', padding=(12, 4, 12, 4))
        self.status_label.pack(fill='x')

    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        search_text = self.search_var.get().strip()
        rows = self.db.get_all_requirements(search_text)
        by_parent = {}
        for row in rows:
            by_parent.setdefault(row['parent_requirement_id'], []).append(row)

        def insert_children(parent_id, parent_node=''):
            for row in sorted(by_parent.get(parent_id, []), key=lambda r: (r['level'], r['summary'])):
                label = f"[{row['level']}] {row['summary']}"
                item = self.tree.insert(parent_node, 'end', iid=row['id'], text=label, values=(LEVEL_LABELS.get(row['level'], str(row['level'])), row['summary']))
                insert_children(row['id'], item)

        insert_children(None)
        self.populate_parent_options(rows)
        self.status_label.config(text=f'Loaded {len(rows)} requirements')

    def populate_parent_options(self, rows):
        options = [''] + [f"{row['summary']} ({row['id'][:8]})" for row in rows]
        self.parent_lookup = {f"{row['summary']} ({row['id'][:8]})": row['id'] for row in rows}
        self.widgets['parent']['values'] = options
        self.widgets['parent'].set('')

    def clear_search(self):
        self.search_var.set('')
        self.refresh_tree()

    def on_tree_select(self, event):
        selection = self.tree.selection()
        if not selection:
            return
        requirement_id = selection[0]
        self.selected_id = requirement_id
        row = self.db.get_requirement(requirement_id)
        if row is None:
            return

        self.widgets['summary'].delete(0, 'end')
        self.widgets['summary'].insert(0, row['summary'] or '')
        self.widgets['description'].delete('1.0', 'end')
        self.widgets['description'].insert('1.0', row['description'] or '')
        self.widgets['level'].set(row['level'])
        parent_label = ''
        if row['parent_requirement_id']:
            parent = self.db.get_requirement(row['parent_requirement_id'])
            if parent:
                parent_label = f"{parent['summary']} ({parent['id'][:8]})"
        self.widgets['parent'].set(parent_label)
        self.widgets['custom_field_1'].delete(0, 'end')
        self.widgets['custom_field_1'].insert(0, row['custom_field_1'] or '')
        self.widgets['custom_field_2'].delete(0, 'end')
        self.widgets['custom_field_2'].insert(0, row['custom_field_2'] or '')
        self.widgets['custom_field_3'].delete(0, 'end')
        self.widgets['custom_field_3'].insert(0, row['custom_field_3'] or '')
        self.widgets['custom_field_4'].delete(0, 'end')
        self.widgets['custom_field_4'].insert(0, row['custom_field_4'] or '')
        self.status_label.config(text=f"Selected requirement {row['id'][:8]}")

    def create_root_requirement(self):
        self.selected_id = None
        self.widgets['summary'].delete(0, 'end')
        self.widgets['description'].delete('1.0', 'end')
        self.widgets['level'].set(0)
        self.widgets['parent'].set('')
        self.widgets['custom_field_1'].delete(0, 'end')
        self.widgets['custom_field_2'].delete(0, 'end')
        self.widgets['custom_field_3'].delete(0, 'end')
        self.widgets['custom_field_4'].delete(0, 'end')
        self.status_label.config(text='Creating new root requirement')

    def create_child_requirement(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo('Create child', 'Select a parent requirement in the tree first.')
            return
        parent_id = selection[0]
        parent = self.db.get_requirement(parent_id)
        if parent is None:
            messagebox.showerror('Create child', 'Selected parent requirement not found.')
            return

        self.selected_id = None
        self.widgets['summary'].delete(0, 'end')
        self.widgets['description'].delete('1.0', 'end')
        child_level = min(parent['level'] + 1, 4)
        self.widgets['level'].set(child_level)
        self.widgets['parent'].set(f"{parent['summary']} ({parent['id'][:8]})")
        self.widgets['custom_field_1'].delete(0, 'end')
        self.widgets['custom_field_2'].delete(0, 'end')
        self.widgets['custom_field_3'].delete(0, 'end')
        self.widgets['custom_field_4'].delete(0, 'end')
        self.status_label.config(text=f"Creating new child for {parent['summary']}")

    def save_changes(self):
        summary = self.widgets['summary'].get().strip()
        description = self.widgets['description'].get('1.0', 'end').strip()
        level = int(self.widgets['level'].get())
        parent_label = self.widgets['parent'].get().strip()
        parent_id = self.parent_lookup.get(parent_label)
        custom_field_1 = self.widgets['custom_field_1'].get().strip()
        custom_field_2 = self.widgets['custom_field_2'].get().strip()
        custom_field_3 = self.widgets['custom_field_3'].get().strip()
        custom_field_4 = self.widgets['custom_field_4'].get().strip()

        if not summary:
            messagebox.showwarning('Save', 'Summary is required.')
            return

        if self.selected_id:
            self.db.update_requirement(
                self.selected_id,
                summary=summary,
                description=description,
                level=level,
                parent_requirement_id=parent_id,
                custom_field_1=custom_field_1,
                custom_field_2=custom_field_2,
                custom_field_3=custom_field_3,
                custom_field_4=custom_field_4,
            )
            self.status_label.config(text='Requirement updated successfully')
        else:
            new_id = self.db.insert_requirement(
                summary=summary,
                description=description,
                level=level,
                parent_requirement_id=parent_id,
                custom_field_1=custom_field_1,
                custom_field_2=custom_field_2,
                custom_field_3=custom_field_3,
                custom_field_4=custom_field_4,
            )
            self.selected_id = new_id
            self.status_label.config(text='Requirement created successfully')

        self.refresh_tree()
        if self.selected_id:
            self.tree.selection_set(self.selected_id)
            self.tree.see(self.selected_id)

    def delete_requirement(self):
        if not self.selected_id:
            messagebox.showinfo('Delete', 'Select a requirement to delete.')
            return
        row = self.db.get_requirement(self.selected_id)
        if row is None:
            messagebox.showerror('Delete', 'Selected requirement does not exist.')
            return
        if messagebox.askyesno('Delete', f"Delete '{row['summary']}' and all child links?"):
            self.db.delete_requirement(self.selected_id)
            self.selected_id = None
            self.refresh_tree()
            self.status_label.config(text='Requirement deleted')
            self.create_root_requirement()

    def run(self):
        self.root.mainloop()


if __name__ == '__main__':
    RequirementsApp().run()
