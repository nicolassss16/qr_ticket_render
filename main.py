
from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import qrcode, os, random, string
import reportlab
from reportlab.pdfgen import canvas
from PIL import Image
from reportlab.lib.pagesizes import letter

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///qr_ticketing.db'
db = SQLAlchemy(app)

class FormData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.String(10), unique=True, nullable=False)
    f_name = db.Column(db.String(50), nullable=False)
    l_name = db.Column(db.String(50), nullable=False)
    dob = db.Column(db.Date, nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    used = db.Column(db.Boolean, default=False)

@app.route("/", methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        f_name = request.form['f_name']
        l_name = request.form['l_name']
        dob = datetime.strptime(request.form['dob'], '%Y-%m-%d').date()
        phone_number = request.form['phone_number']

        if len(phone_number) > 10:
            return render_template("index.html", error="Phone number cannot be longer than 10 digits")

        ticket_id = generate_ticket_id()

        form_data = FormData(ticket_id=ticket_id, f_name=f_name, l_name=l_name, dob=dob, phone_number=phone_number)
        db.session.add(form_data)
        db.session.commit()

        generate_qr_code(ticket_id)
        return render_template("success.html", ticket_id=ticket_id)

    return render_template("index.html")

def generate_ticket_id():
    return ''.join(random.choices(string.digits, k=10))

def generate_qr_code(ticket_id):
    url = f"https://qr-ticketing-system.onrender.com/verify/{ticket_id}"
    img = qrcode.make(url)
    os.makedirs("static/qrcodes", exist_ok=True)
    img.save(f"static/qrcodes/{ticket_id}.png")

@app.route("/verify/<ticket_id>")
def verify_qr(ticket_id):
    ticket = FormData.query.filter_by(ticket_id=ticket_id).first()
    if ticket:
        if ticket.used:
            return render_template("used.html", ticket_id=ticket_id)
        else:
            ticket.used = True
            db.session.commit()
            return render_template("verified.html", ticket=ticket)
    else:
        return render_template("error.html", message="Ticket no válido.")

@app.route("/get", methods=['GET'])
def get_data():
    data = FormData.query.all()
    return render_template("get_data.html", data=data)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/pdf/<ticket_id>")
def download_pdf(ticket_id):
    pdf_filename = f"ticket_{ticket_id}.pdf"
    pdf_path = generate_pdf(ticket_id, pdf_filename)
    return send_file(pdf_path, as_attachment=True)

def generate_pdf(ticket_id, filename):
    pdf_dir = os.path.join(app.root_path, "pdf")
    os.makedirs(pdf_dir, exist_ok=True)
    pdf_path = os.path.join(pdf_dir, filename)
    c = canvas.Canvas(pdf_path, pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(letter[0] / 2, letter[1] - 50, "QR TICKETING SYSTEM")
    c.setFont("Helvetica", 12)
    form_data = FormData.query.filter_by(ticket_id=ticket_id).first()

    if form_data:
        c.drawString(100, 700, f"Ticket ID: {form_data.ticket_id}")
        c.drawString(100, 680, f"Name: {form_data.f_name} {form_data.l_name}")
        c.drawString(100, 660, f"DOB: {form_data.dob.strftime('%Y-%m-%d')}")
        c.drawString(100, 640, f"Phone Number: {form_data.phone_number}")
        img_path = f"static/qrcodes/{form_data.ticket_id}.png"
        if os.path.exists(img_path):
            img = Image.open(img_path)
            img_width, img_height = img.size
            aspect_ratio = img_width / img_height
            img_width = 100
            img_height = img_width / aspect_ratio
            c.drawInlineImage(img_path, 100, 600 - img_height, width=img_width, height=img_height)

    c.setFont("Helvetica", 10)
    c.drawCentredString(letter[0] / 2, 30, "Made by Sarthak Lamba")
    c.drawCentredString(letter[0] / 2, 15, "Contact: samlamba29@gmail.com")
    c.showPage()
    c.save()
    return pdf_path

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
