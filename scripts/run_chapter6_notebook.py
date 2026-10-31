"""Execute Chapter 6 only in a clean kernel and retain its outputs in the main notebook."""
import os
import sys
import ast
from pathlib import Path
import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK = ROOT / 'TieuLuan_HeThongThongMinh.ipynb'


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    notebook = nbformat.read(NOTEBOOK, as_version=4)
    indices = [i for i,c in enumerate(notebook.cells) if 'chapter6' in c.metadata.get('tags', [])]
    if not indices:
        raise RuntimeError('Build Chapter 6 first')
    isolated = nbformat.v4.new_notebook(cells=[notebook.cells[i] for i in indices])
    if '--diagrams-only' in sys.argv:
        diagram_index = next(i for i in indices if notebook.cells[i].source.startswith('def ch6_draw_diagram'))
        config_source = next(notebook.cells[i].source for i in indices
                             if notebook.cells[i].source.startswith('import os, sys'))
        figure_function = next(ast.get_source_segment(config_source, node)
                               for node in ast.parse(config_source).body
                               if isinstance(node, ast.FunctionDef) and node.name=='ch6_figure')
        bootstrap = ('from pathlib import Path\nimport numpy as np\nimport matplotlib.pyplot as plt\n'
                     'from matplotlib.patches import FancyBboxPatch\nimport networkx as nx\n'
                     "plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'figure.dpi':110})\n"
                     f'CH6_OUT=Path({str(ROOT / "reports/chapter6")!r})\nCH6_FIGURES=[]\n' + figure_function)
        indices = [None, diagram_index]
        isolated = nbformat.v4.new_notebook(cells=[nbformat.v4.new_code_cell(bootstrap), notebook.cells[diagram_index]])
    isolated.metadata.kernelspec = dict(display_name='Python 3', language='python', name='python3')
    # Avoid writing IPython history into the user's profile.
    os.environ['IPYTHONDIR'] = str(ROOT / '.ipynb_checkpoints/ch6_ipython')
    os.environ['MPLCONFIGDIR'] = str(ROOT / '.ipynb_checkpoints/ch6_matplotlib')

    def on_cell_start(cell, cell_index, **kwargs):
        if cell.cell_type == 'code':
            print(f'Executing Chapter 6 cell {cell_index+1}/{len(indices)}: {cell.source.splitlines()[0][:90]}', flush=True)

    client = NotebookClient(isolated, timeout=240, kernel_name='python3', allow_errors=False,
        resources={'metadata': {'path': str(ROOT)}}, on_cell_start=on_cell_start,
        extra_arguments=['--HistoryManager.hist_file=:memory:'])
    try:
        client.execute()
    finally:
        # Keep a failed cell's traceback too, so failures are reviewable and rerunnable.
        for index, cell in zip(indices, isolated.cells):
            if index is not None:
                notebook.cells[index] = cell
        nbformat.validate(notebook)
        nbformat.write(notebook, NOTEBOOK)
    errors = [o for c in isolated.cells for o in c.get('outputs', []) if o.output_type == 'error']
    if errors:
        raise RuntimeError(f'Chapter 6 has {len(errors)} failed cells')
    print('PASS: Requested Chapter 6 cells completed in a clean kernel; outputs saved. Chapters 1–5 were not executed.', flush=True)


if __name__ == '__main__':
    main()
