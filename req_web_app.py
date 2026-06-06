"""Web frontend for the requirements tool.

This module exposes a small Flask JSON API used by the web UI under
`templates/` and `static/`. It also provides a simple `get_db()` helper
that attaches a `RequirementDatabase` instance to the request `g` object.

The changes here add lightweight input validation and JSON error
handlers so API clients receive consistent JSON error objects.
"""

from typing import Optional, Dict, Any

import logging
from flask import Flask, request, jsonify, abort, render_template, g
from requirements_db import RequirementDatabase


logging.basicConfig(level=logging.INFO)
app = Flask(__name__, static_folder='static', template_folder='templates')


def get_db() -> RequirementDatabase:
    """Get or create a database connection for the current request context.

    The `RequirementDatabase` instance is stored on `flask.g` so each
    request gets its own connection that can be closed in
    `teardown_appcontext`.
    """
    if 'db' not in g:
        # create a new DB object for the request lifecycle
        g.db = RequirementDatabase('requirements.db')
    return g.db


@app.teardown_appcontext
def close_db(exception):
    """Close the database connection at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def row_to_dict(row) -> Optional[Dict[str, Any]]:
    """Convert a sqlite3.Row (or None) to a JSON-serializable dict.

    Returns `None` if `row` is falsy to preserve the previous behavior.
    """
    if row is None:
        return None
    return {k: row[k] for k in row.keys()}

    summary = str(data.get('summary', '')).strip()
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/requirements', methods=['GET'])
def list_requirements():
    q = request.args.get('q', '')
    rows = get_db().get_all_requirements(q)
    return jsonify([row_to_dict(r) for r in rows])


@app.route('/api/requirements/<requirement_id>', methods=['GET'])
def get_requirement(requirement_id):
    row = get_db().get_requirement(requirement_id)
    if row is None:
        abort(404, description='Requirement not found')
    return jsonify(row_to_dict(row))


@app.route('/api/requirements', methods=['POST'])
def create_requirement():
    data = request.get_json(force=True)
    summary = (data.get('summary') or '').strip()
    if not summary:
        abort(400, description='Summary is required')
    # Basic validation and normalization for optional fields
    description = data.get('description', '') or ''
    level_raw = data.get('level', 0)
    try:
        level = int(level_raw) if level_raw is not None and str(level_raw) != '' else 0
    except (ValueError, TypeError):
        abort(400, description='Invalid level value')
    parent_requirement_id = data.get('parent_requirement_id')
    custom_field_1 = data.get('custom_field_1')
    custom_field_2 = data.get('custom_field_2')
    custom_field_3 = data.get('custom_field_3')
    custom_field_4 = data.get('custom_field_4')

    new_id = get_db().insert_requirement(
        summary=summary,
        description=description,
        level=level,
        parent_requirement_id=parent_requirement_id,
        custom_field_1=custom_field_1,
        custom_field_2=custom_field_2,
        custom_field_3=custom_field_3,
        custom_field_4=custom_field_4,
    )

    resp = get_db().get_requirement(new_id)
    return (jsonify(row_to_dict(resp)), 201)


@app.route('/api/requirements/<requirement_id>', methods=['PUT'])
def update_requirement(requirement_id):
    data = request.get_json(force=True)
    row = get_db().get_requirement(requirement_id)
    if row is None:
        abort(404, description='Requirement not found')

    summary = data.get('summary')
    description = data.get('description')
    level_raw = data.get('level')
    parent_requirement_id = data.get('parent_requirement_id')
    custom_field_1 = data.get('custom_field_1')
    custom_field_2 = data.get('custom_field_2')
    custom_field_3 = data.get('custom_field_3')
    custom_field_4 = data.get('custom_field_4')

    get_db().update_requirement(
        requirement_id,
        summary=summary,
        description=description,
        level=int(level_raw) if level_raw is not None and str(level_raw) != '' else None,
        parent_requirement_id=parent_requirement_id,
        custom_field_1=custom_field_1,
        custom_field_2=custom_field_2,
        custom_field_3=custom_field_3,
        custom_field_4=custom_field_4,
    )

    resp = get_db().get_requirement(requirement_id)
    return jsonify(row_to_dict(resp))


@app.route('/api/requirements/<requirement_id>', methods=['DELETE'])
def delete_requirement(requirement_id):
    row = get_db().get_requirement(requirement_id)
    if row is None:
        abort(404, description='Requirement not found')
    get_db().delete_requirement(requirement_id)
    return ('', 204)


@app.route('/api/parents', methods=['GET'])
def parent_options():
    opts = get_db().get_parent_options()
    return jsonify([{'id': id_, 'label': label} for id_, label in opts])


@app.errorhandler(400)
def handle_bad_request(err):
    """Return JSON for 400 errors instead of HTML pages."""
    description = getattr(err, 'description', str(err))
    return jsonify({'error': 'bad_request', 'message': description}), 400


@app.errorhandler(404)
def handle_not_found(err):
    description = getattr(err, 'description', 'Not found')
    return jsonify({'error': 'not_found', 'message': description}), 404


@app.errorhandler(500)
def handle_server_error(err):
    app.logger.exception('Unhandled exception')
    return jsonify({'error': 'server_error', 'message': 'Internal server error'}), 500


if __name__ == '__main__':
    app.run(debug=True)
