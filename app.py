import cv2
import time
import threading
from flask import Response, Flask, render_template

# Image frame sent to the Flask object
global right_video_frame
right_video_frame = None

global left_video_frame
left_video_frame = None

# Use locks for thread-safe viewing of frames in multiple browsers
global right_thread_lock 
right_thread_lock = threading.Lock()

global left_thread_lock 
left_thread_lock = threading.Lock()

# GStreamer Pipeline to access the Raspberry Pi camera
RIGHT_GSTREAMER_PIPELINE = 'nvarguscamerasrc sensor-id=1 ! video/x-raw(memory:NVMM), width=3280, height=2464, format=(string)NV12, framerate=21/1 ! nvvidconv flip-method=0 ! video/x-raw, width=960, height=616, format=(string)BGRx ! videoconvert ! video/x-raw, format=(string)BGR ! appsink wait-on-eos=false max-buffers=1 drop=True'

LEFT_GSTREAMER_PIPELINE = 'nvarguscamerasrc sensor-id=0 ! video/x-raw(memory:NVMM), width=3280, height=2464, format=(string)NV12, framerate=21/1 ! nvvidconv flip-method=2 ! video/x-raw, width=960, height=616, format=(string)BGRx ! videoconvert ! video/x-raw, format=(string)BGR ! appsink wait-on-eos=false max-buffers=1 drop=True'

# Create the Flask object for the application
app = Flask(__name__)

def rightCaptureFrames():
    global right_video_frame, right_thread_lock

    # Video capturing from OpenCV
    right_video_capture = cv2.VideoCapture(RIGHT_GSTREAMER_PIPELINE, cv2.CAP_GSTREAMER)

    while True and right_video_capture.isOpened():
        return_key, frame = right_video_capture.read()
        if not return_key:
            break

        # Create a copy of the frame and store it in the global variable,
        # with thread safe access
        with right_thread_lock:
            right_video_frame = frame.copy()
        
        key = cv2.waitKey(30) & 0xff
        if key == 27:
            break

    right_video_capture.release()


def leftCaptureFrames():
    global left_video_frame, left_thread_lock

    # Video capturing from OpenCV
    left_video_capture = cv2.VideoCapture(LEFT_GSTREAMER_PIPELINE, cv2.CAP_GSTREAMER)

    while True and left_video_capture.isOpened():
        return_key, frame = left_video_capture.read()
        if not return_key:
            break

        # Create a copy of the frame and store it in the global variable,
        # with thread safe access
        with left_thread_lock:
            left_video_frame = frame.copy()
        
        key = cv2.waitKey(30) & 0xff
        if key == 27:
            break

    left_video_capture.release()




        
def rightEncodeFrame():
    global right_thread_lock
    while True:
        # Acquire right_thread_lock to access the global right_video_frame object
        with right_thread_lock:
            global right_video_frame
            if right_video_frame is None:
                continue
            return_key, right_encoded_image = cv2.imencode(".jpg", right_video_frame)
            if not return_key:
                continue

        # Output image as a byte array
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
            bytearray(right_encoded_image) + b'\r\n')



def leftEncodeFrame():
    global left_thread_lock
    while True:
        # Acquire left_thread_lock to access the global left_video_frame object
        with left_thread_lock:
            global left_video_frame
            if left_video_frame is None:
                continue
            return_key, left_encoded_image = cv2.imencode(".jpg", left_video_frame)
            if not return_key:
                continue

        # Output image as a byte array
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
            bytearray(left_encoded_image) + b'\r\n')




@app.route("/")
def showIndex():
    return render_template("index.html")

@app.route("/right")
def rightStreamFrames():
    return Response(rightEncodeFrame(), mimetype = "multipart/x-mixed-replace; boundary=frame")



@app.route("/left")
def leftStreamFrames():
    return Response(leftEncodeFrame(), mimetype = "multipart/x-mixed-replace; boundary=frame")



# check to see if this is the main thread of execution
if __name__ == '__main__':

    # Create a thread and attach the method that captures the image frames, to it
    right_process_thread = threading.Thread(target=rightCaptureFrames)
    right_process_thread.daemon = True

    left_process_thread = threading.Thread(target=leftCaptureFrames)
    left_process_thread.daemon = True

    # Start the thread
    right_process_thread.start()
    left_process_thread.start()

    # start the Flask Web Application
    # While it can be run on any feasible IP, IP = 0.0.0.0 renders the web app on
    # the host machine's localhost and is discoverable by other machines on the same network 
    app.run("10.0.0.195", port="5000")