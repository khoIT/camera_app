#!/usr/bin/env python
import os
import shutil
from flask import Flask, render_template, request, \
    Response, send_file, redirect, url_for
from camera import Camera
from datetime import datetime, timedelta
from send_email import Email
from faceid_api import FaceIDApi
import image_utils

app = Flask(__name__)
camera = None
mail_server = None
mail_conf = "static/mail_conf.json"
api_volley = FaceIDApi()
api_volley.login('admin', 'AdminFaceID@2020')


def get_camera():
    global camera
    if not camera:
        camera = Camera()

    return camera

def get_mail_server():
    global mail_server
    if not mail_server:
        mail_server = Email(mail_conf)

    return mail_server

@app.route('/')
def root():
    return redirect(url_for('index'))

@app.route('/index/')
def index():
    return render_template('index.html')

def gen(camera):
    while True:
        frame = camera.get_feed()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video_feed/')
def video_feed():
    camera = get_camera()
    return Response(gen(camera),
        mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/capture/')
def capture():
    camera = get_camera()
    stamp, img = camera.capture()

    scaled_image, gray = image_utils.img_preprocess(img)

    faces = image_utils.detect_face(gray)
     # Check if have face
    if (len(faces) != 0):
        [x, y, w, h] = image_utils.biggest_face(faces)
        [x, y, w, h] = [int(x/0.3), int(y/0.3), int(w/0.3), int(h/0.3)]
        crop_img = image_utils.img_crop(img, x, y, w, h)
        img = image_utils.img_draw_rect(img, x, y, w, h)

        if (w < 72):
            # Size of face is too small
            print('Please look closer')
        else:
            # Send FaceID api
            base64_img = image_utils.img2base64(crop_img)
            if (base64_img == ''):
                print('Error when encode image')
            else:
                res = api_volley.verify(base64_img)
                import pdb; pdb.set_trace()
                print(res)
    else:
        print('Please look closer')
    # import pdb; pdb.set_trace()
    # return redirect(url_for('show_capture', timestamp=stamp))
    return render_template('capture.html', stamp=stamp, path=stamp_file(stamp))

def stamp_file(timestamp):
    return 'captures/' + timestamp +".jpg"

@app.route('/capture/image/<timestamp>', methods=['POST', 'GET'])
def show_capture(timestamp):
    path = stamp_file(timestamp)

    email_msg = None
    if request.method == 'POST':
        if request.form.get('email'):
            email = get_mail_server()
            email_msg = email.send_email('static/{}'.format(path),
                request.form['email'])
        else:
            email_msg = "Email field empty!"

    return render_template('capture.html',
        stamp=timestamp, path=path, email_msg=email_msg)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
