from flask import Flask
app = Flask(__name__)

@app.route('/exhaustive-entities/')
@app.route('/exhaustive-entities/<doc_id>')
@app.route('/exhaustive-entities/<doc_id>')
@app.route('/exhaustive-relations/')
@app.route('/hello/<name>')
def hello(name=None):
        return render_template('hello.html', name=name)k
@app.route('/selective-relations/')
@app.route('/')
def hello_world():
    return 'Hello, World!'

if __name__ == "__main__":
    app.run()
