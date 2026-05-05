# main.py
import os
from flask import Flask, render_template, Response, redirect, request, session, abort, url_for
from camera import VideoCamera
from camera2 import VideoCamera2
import cv2
import numpy as np
import shutil
import datetime
import PIL.Image
from PIL import Image
import imagehash
import mysql.connector
from werkzeug.utils import secure_filename
from ultralytics import YOLO

mydb = mysql.connector.connect(
  host="localhost",
  user="root",
  password="",
  charset="utf8",
  database="face_expression_recognition"

)
app = Flask(__name__)
app.secret_key = 'abcdef'

UPLOAD_FOLDER = 'static/upload'
ALLOWED_EXTENSIONS = { 'png', 'jpg', 'jpeg', 'gif'}
model1 = YOLO("yolov8n.pt")
current_camera = None
video_stream_path = None
last_status = "Normal"
last_prob = 0.0
stream_finished = False

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    ff=open("det.txt","w")
    ff.write("1")
    ff.close()

    ff1=open("photo.txt","w")
    ff1.write("1")
    ff1.close()

    ff11=open("img.txt","w")
    ff11.write("1")
    ff11.close()

    ff=open("person.txt","w")
    ff.write("")
    ff.close()
    return render_template('index.html')

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/login_admin', methods=['GET', 'POST'])
def login_admin():
    msg=""
    if request.method=='POST':
        uname=request.form['uname']
        pwd=request.form['pass']
        cursor = mydb.cursor()
        cursor.execute('SELECT * FROM admin WHERE username = %s AND password = %s', (uname, pwd))
        account = cursor.fetchone()
        if account:
            #session['loggedin'] = True
            #session['username'] = account['username']
            # Redirect to home page
            return redirect(url_for('admin'))
        else:
            # Account doesnt exist or username/password incorrect
            msg = 'Incorrect username/password!'
    return render_template('login_admin.html',msg=msg)

@app.route('/admin',methods=['POST','GET'])
def admin():
    act=request.args.get("act")
    mycursor = mydb.cursor()
    if request.method == 'POST':
        
        detail = request.form['detail']

        mycursor.execute("SELECT max(id)+1 FROM train_data")
        maxid = mycursor.fetchone()[0]
        if maxid is None:
            maxid=1

        sql = "INSERT INTO train_data(id, utype, detail,fimg) VALUES (%s, %s, %s, %s)"
        val = (maxid, '', detail, '')
        print(sql)
        mycursor.execute(sql, val)
        mydb.commit()
        return redirect(url_for('add_photo',vid=maxid)) 

    mycursor.execute("SELECT * FROM train_data")
    value = mycursor.fetchall()

    ###
    if act=="del":
        did=request.args.get("did")

        mycursor.execute("SELECT count(*) FROM vt_face where vid=%s",(did,))
        cn = mycursor.fetchone()[0]
        if cn>0:
            mycursor.execute("SELECT * FROM vt_face where vid=%s",(did,))
            dd = mycursor.fetchall()
            for ds in dd:
                os.remove("static/frame/"+ds[2])

            mycursor.execute("delete from vt_face where vid=%s",(did,))
            mydb.commit()
                
        
        mycursor.execute("delete from train_data where id=%s",(did,))
        mydb.commit()
        return redirect(url_for('admin')) 
    ###
        
    return render_template('admin.html',value=value)

@app.route('/admin2',methods=['POST','GET'])
def admin2():
    act=request.args.get("act")
    mycursor = mydb.cursor()
    
    mycursor.execute("SELECT * FROM train_data")
    value = mycursor.fetchall()

    ###
    if act=="del":
        did=request.args.get("did")

        mycursor.execute("SELECT count(*) FROM vt_face where vid=%s",(did,))
        cn = mycursor.fetchone()[0]
        if cn>0:
            mycursor.execute("SELECT * FROM vt_face where vid=%s",(did,))
            dd = mycursor.fetchall()
            '''for ds in dd:
                os.remove("static/frame/"+ds[2])
                os.remove("images_db/"+ds[2])'''

            mycursor.execute("delete from vt_face where vid=%s",(did,))
            mydb.commit()
                
        
        mycursor.execute("delete from train_data where id=%s",(did,))
        mydb.commit()
        return redirect(url_for('admin')) 
    ###
        
    return render_template('admin2.html',value=value)


@app.route('/home', methods=['GET', 'POST'])
def home():
    return render_template('home.html')




@app.route('/register', methods=['GET', 'POST'])
def register():
    #import student
    msg=""
    if request.method=='POST':
        name=request.form['name']
        mobile=request.form['mobile']
        email=request.form['email']
        address=request.form['address']
        uname=request.form['uname']
        pass1=request.form['pass']
    
        cursor = mydb.cursor()
        sql = "INSERT INTO register(name,mobile,email,address,uname,pass) VALUES (%s, %s, %s, %s, %s, %s)"
        val = (name,mobile,email,address,uname,pass1)
        cursor.execute(sql, val)
        mydb.commit()            
        print(cursor.rowcount, "Registered Success")
        result="sucess"
        if cursor.rowcount==1:
            return redirect(url_for('login'))
        else:
            msg='Already Exist'
    return render_template('register.html',msg=msg)

@app.route('/capture', methods=['GET', 'POST'])
def capture():
    act=""
    uname=""
    if 'username' in session:
        uname = session['username']

    cursor = mydb.cursor()
    cursor.execute('SELECT * FROM face_reg where uname=%s',(uname, ))
    data = cursor.fetchall()
    
    if request.method=='GET':
        act = request.args.get('act')
    if request.method=='POST':
        act="yes"
        ftype=request.form['ftype']

        mycursor = mydb.cursor()
        mycursor.execute("SELECT max(id)+1 FROM face_reg")
        maxid = mycursor.fetchone()[0]
        if maxid is None:
            maxid=1
            
        ss=uname+str(maxid)+".jpg"
        path="static/photo/"+ss
        shutil.copy('faces/f1.jpg', path)
        cursor = mydb.cursor()
        sql = "INSERT INTO face_reg(id,uname,fimage,ftype) VALUES (%s, %s, %s, %s)"
        val = (maxid,uname,ss,ftype)
        cursor.execute(sql, val)
        mydb.commit()
        
        return redirect(url_for('capture',act=act,uname=uname))
    return render_template('capture.html',act=act, uname=uname, data=data)

def getImagesAndLabels(path):

    
    detector = cv2.CascadeClassifier("haarcascade_frontalface_default.xml");

    imagePaths = [os.path.join(path,f) for f in os.listdir(path)]     
    faceSamples=[]
    ids = []

    for imagePath in imagePaths:

        PIL_img = Image.open(imagePath).convert('L') # convert it to grayscale
        img_numpy = np.array(PIL_img,'uint8')

        id = int(os.path.split(imagePath)[-1].split(".")[1])
        faces = detector.detectMultiScale(img_numpy)

        for (x,y,w,h) in faces:
            faceSamples.append(img_numpy[y:y+h,x:x+w])
            ids.append(id)

    return faceSamples,ids


@app.route('/add_photo',methods=['POST','GET'])
def add_photo():
    vid = request.args.get('vid')
    ff1=open("photo.txt","w")
    ff1.write("2")
    ff1.close()

    #ff2=open("mask.txt","w")
    #ff2.write("face")
    #ff2.close()
    act = request.args.get('act')

    cursor = mydb.cursor()
    
    cursor.execute("SELECT * FROM train_data where id=%s",(vid,))
    value = cursor.fetchone()
    name=value[2]
    
    ff=open("user.txt","w")
    ff.write(name)
    ff.close()

    ff=open("user1.txt","w")
    ff.write(vid)
    ff.close()
    

    
    
    if request.method=='POST':
        vid=request.form['vid']
        fimg="v"+vid+".jpg"
        

        cursor.execute('delete from vt_face WHERE vid = %s', (vid, ))
        mydb.commit()

        

        ff=open("det.txt","r")
        v=ff.read()
        ff.close()
        vv=int(v)
        v1=vv-1
        vface1="User."+vid+"."+str(v1)+".jpg"
        i=2
        while i<vv:
            
            cursor.execute("SELECT max(id)+1 FROM vt_face")
            maxid = cursor.fetchone()[0]
            if maxid is None:
                maxid=1
            vface="User."+vid+"."+str(i)+".jpg"
            sql = "INSERT INTO vt_face(id, vid, vface) VALUES (%s, %s, %s)"
            val = (maxid, vid, vface)
            print(val)
            cursor.execute(sql,val)
            mydb.commit()
            i+=1

        
            
        cursor.execute('update train_data set fimg=%s WHERE id = %s', (vface1, vid))
        mydb.commit()
        shutil.copy('static/faces/f1.jpg', 'static/photo/'+vface1)

        
        ##########
        
        ##Training face
        # Path for face image database
        path = 'dataset'

        recognizer = cv2.face.LBPHFaceRecognizer_create()

        # function to get the images and label data
        

        print ("\n [INFO] Training faces. It will take a few seconds. Wait ...")
        faces,ids = getImagesAndLabels(path)
        recognizer.train(faces, np.array(ids))

        # Save the model into trainer/trainer.yml
        recognizer.write('trainer/trainer.yml') # recognizer.save() worked on Mac, but not on Pi

        # Print the numer of faces trained and end program
        print("\n [INFO] {0} faces trained. Exiting Program".format(len(np.unique(ids))))






        #################################################
        cursor = mydb.cursor()
        cursor.execute("SELECT * FROM vt_face where vid=%s",(vid, ))
        dt = cursor.fetchall()
        for rs in dt:
            ##Preprocess
            path="static/frame/"+rs[2]
            path2="static/process1/"+rs[2]
            mm2 = PIL.Image.open(path).convert('L')
            rz = mm2.resize((200,200), PIL.Image.Resampling.LANCZOS)
            rz.save(path2)
            
            '''img = cv2.imread(path2) 
            dst = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 15)
            path3="static/process2/"+rs[2]
            cv2.imwrite(path3, dst)'''
            #noice
            img = cv2.imread('static/process1/'+rs[2]) 
            dst = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 15)
            fname2='ns_'+rs[2]
            cv2.imwrite("static/process1/"+fname2, dst)
            ######
            ##bin
            image = cv2.imread('static/process1/'+rs[2])
            original = image.copy()
            kmeans = kmeans_color_quantization(image, clusters=4)

            # Convert to grayscale, Gaussian blur, adaptive threshold
            gray = cv2.cvtColor(kmeans, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (3,3), 0)
            thresh = cv2.adaptiveThreshold(blur,255,cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY_INV,21,2)
            
            # Draw largest enclosing circle onto a mask
            mask = np.zeros(original.shape[:2], dtype=np.uint8)
            cnts = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cnts = cnts[0] if len(cnts) == 2 else cnts[1]
            cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
            for c in cnts:
                ((x, y), r) = cv2.minEnclosingCircle(c)
                cv2.circle(image, (int(x), int(y)), int(r), (36, 255, 12), 2)
                cv2.circle(mask, (int(x), int(y)), int(r), 255, -1)
                break
            
            # Bitwise-and for result
            result = cv2.bitwise_and(original, original, mask=mask)
            result[mask==0] = (0,0,0)

            
            ###cv2.imshow('thresh', thresh)
            ###cv2.imshow('result', result)
            ###cv2.imshow('mask', mask)
            ###cv2.imshow('kmeans', kmeans)
            ###cv2.imshow('image', image)
            ###cv2.waitKey()

            cv2.imwrite("static/process1/bin_"+rs[2], thresh)
            

            ###RPN - Segment
            img = cv2.imread('static/process1/'+rs[2])
            gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
            ret, thresh = cv2.threshold(gray,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)

            
            kernel = np.ones((3,3),np.uint8)
            opening = cv2.morphologyEx(thresh,cv2.MORPH_OPEN,kernel, iterations = 2)

            # sure background area
            sure_bg = cv2.dilate(opening,kernel,iterations=3)

            # Finding sure foreground area
            dist_transform = cv2.distanceTransform(opening,cv2.DIST_L2,5)
            ret, sure_fg = cv2.threshold(dist_transform,0.7*dist_transform.max(),255,0)

            # Finding unknown region
            sure_fg = np.uint8(sure_fg)
            segment = cv2.subtract(sure_bg,sure_fg)
            img = Image.fromarray(img)
            segment = Image.fromarray(segment)
            path3="static/process2/fg_"+rs[2]
            segment.save(path3)
            ####
            img = cv2.imread('static/process2/fg_'+rs[2])
            gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
            ret, thresh = cv2.threshold(gray,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)

            
            kernel = np.ones((3,3),np.uint8)
            opening = cv2.morphologyEx(thresh,cv2.MORPH_OPEN,kernel, iterations = 2)

            # sure background area
            sure_bg = cv2.dilate(opening,kernel,iterations=3)

            # Finding sure foreground area
            dist_transform = cv2.distanceTransform(opening,cv2.DIST_L2,5)
            ret, sure_fg = cv2.threshold(dist_transform,0.7*dist_transform.max(),255,0)

            # Finding unknown region
            sure_fg = np.uint8(sure_fg)
            segment = cv2.subtract(sure_bg,sure_fg)
            img = Image.fromarray(img)
            segment = Image.fromarray(segment)
            path3="static/process2/fg_"+rs[2]
            segment.save(path3)
            '''
            img = cv2.imread(path2)
            gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
            ret, thresh = cv2.threshold(gray,0,255,cv2.THRESH_BINARY_INV+cv2.THRESH_OTSU)

            # noise removal
            kernel = np.ones((3,3),np.uint8)
            opening = cv2.morphologyEx(thresh,cv2.MORPH_OPEN,kernel, iterations = 2)

            # sure background area
            sure_bg = cv2.dilate(opening,kernel,iterations=3)

            # Finding sure foreground area
            dist_transform = cv2.distanceTransform(opening,cv2.DIST_L2,5)
            ret, sure_fg = cv2.threshold(dist_transform,0.7*dist_transform.max(),255,0)

            # Finding unknown region
            sure_fg = np.uint8(sure_fg)
            segment = cv2.subtract(sure_bg,sure_fg)
            img = Image.fromarray(img)
            segment = Image.fromarray(segment)
            path3="static/process2/"+rs[2]
            segment.save(path3)
            '''
            #####
            image = cv2.imread(path2)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            edged = cv2.Canny(gray, 50, 100)
            image = Image.fromarray(image)
            edged = Image.fromarray(edged)
            path4="static/process3/"+rs[2]
            edged.save(path4)
            ##
        ###
        cursor.execute("SELECT count(*) FROM vt_face where vid=%s",(vid, ))
        cnt = cursor.fetchone()[0]
        #if cnt>10:
        return redirect(url_for('view_photo',vid=vid,act='success'))
        #else:
        #    return redirect(url_for('message',vid=vid))
    
    cursor.execute("SELECT * FROM train_data")
    data = cursor.fetchall()
    return render_template('add_photo.html',data=data, vid=vid)

def kmeans_color_quantization(image, clusters=8, rounds=1):
    h, w = image.shape[:2]
    samples = np.zeros([h*w,3], dtype=np.float32)
    count = 0

    for x in range(h):
        for y in range(w):
            samples[count] = image[x][y]
            count += 1

    compactness, labels, centers = cv2.kmeans(samples,
            clusters, 
            None,
            (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10000, 0.0001), 
            rounds, 
            cv2.KMEANS_RANDOM_CENTERS)

    centers = np.uint8(centers)
    res = centers[labels.flatten()]
    return res.reshape((image.shape))

@app.route('/view_photo',methods=['POST','GET'])
def view_photo():
    ff1=open("photo.txt","w")
    ff1.write("1")
    ff1.close()
    vid=""
    value=[]
    if request.method=='GET':
        vid = request.args.get('vid')
        mycursor = mydb.cursor()
        mycursor.execute("SELECT * FROM vt_face where vid=%s",(vid, ))
        value = mycursor.fetchall()

    if request.method=='POST':
        print("Training")
        vid=request.form['vid']
        
        #shutil.copy('static/img/11.png', 'static/process4/'+rs[2])
       
        #return redirect(url_for('view_photo1',vid=vid))
        
    return render_template('view_photo.html', result=value,vid=vid)



@app.route('/pro1',methods=['POST','GET'])
def pro1():
    s1=""
    vid = request.args.get('vid')
    act = request.args.get('act')
    value=[]
    
        
    mycursor = mydb.cursor()
    mycursor.execute("SELECT count(*) FROM vt_face where vid=%s",(vid, ))
    cnt = mycursor.fetchone()[0]

    if act is None:
        act=1
        
    act1=int(act)-1
    act2=int(act)+1
    act3=str(act2)
    
    n=10
    if act1<n:
        s1="1"
        mycursor.execute("SELECT * FROM vt_face where vid=%s limit %s,1",(vid, act1))
        value = mycursor.fetchone()
    else:
        s1="2"

    
    return render_template('pro1.html', value=value,vid=vid, act=act3,s1=s1)

@app.route('/pro2',methods=['POST','GET'])
def pro2():
    s1=""
    vid = request.args.get('vid')
    act = request.args.get('act')
    value=[]
    
        
    mycursor = mydb.cursor()
    mycursor.execute("SELECT count(*) FROM vt_face where vid=%s",(vid, ))
    cnt = mycursor.fetchone()[0]

    if act is None or act=='0':
        act=1
        
    act1=int(act)-1
    act2=int(act)+1
    act3=str(act2)
    
    n=10
    if act1<n:
        s1="1"
        mycursor.execute("SELECT * FROM vt_face where vid=%s limit %s,1",(vid, act1))
        value = mycursor.fetchone()
    else:
        s1="2"

    
    return render_template('pro2.html', value=value,vid=vid, act=act3,s1=s1)

@app.route('/pro3',methods=['POST','GET'])
def pro3():
    s1=""
    vid = request.args.get('vid')
    act = request.args.get('act')
    value=[]
    
        
    mycursor = mydb.cursor()
    mycursor.execute("SELECT count(*) FROM vt_face where vid=%s",(vid, ))
    cnt = mycursor.fetchone()[0]

    if act is None:
        act=1
        
    act1=int(act)-1
    act2=int(act)+1
    act3=str(act2)
    
    n=10
    if act1<n:
        s1="1"
        mycursor.execute("SELECT * FROM vt_face where vid=%s limit %s,1",(vid, act1))
        value = mycursor.fetchone()
    else:
        s1="2"

    
    return render_template('pro3.html', value=value,vid=vid, act=act3,s1=s1)

@app.route('/pro4',methods=['POST','GET'])
def pro4():
    s1=""
    vid = request.args.get('vid')
    act = request.args.get('act')
    value=[]
    
        
    mycursor = mydb.cursor()
    mycursor.execute("SELECT count(*) FROM vt_face where vid=%s",(vid, ))
    cnt = mycursor.fetchone()[0]

    if act is None:
        act=1
        
    act1=int(act)-1
    act2=int(act)+1
    act3=str(act2)
    
    n=10
    if act1<n:
        s1="1"
        mycursor.execute("SELECT * FROM vt_face where vid=%s limit %s,1",(vid, act1))
        value = mycursor.fetchone()
    else:
        s1="2"

    
    return render_template('pro4.html', value=value,vid=vid, act=act3,s1=s1)

@app.route('/pro5',methods=['POST','GET'])
def pro5():
    s1=""
    vid = request.args.get('vid')
    act = request.args.get('act')
    value=[]
    
        
    mycursor = mydb.cursor()
    mycursor.execute("SELECT count(*) FROM vt_face where vid=%s",(vid, ))
    cnt = mycursor.fetchone()[0]

    if act is None:
        act=1
        
    act1=int(act)-1
    act2=int(act)+1
    act3=str(act2)
    
    n=10
    if act1<n:
        s1="1"
        mycursor.execute("SELECT * FROM vt_face where vid=%s limit %s,1",(vid, act1))
        value = mycursor.fetchone()
    else:
        s1="2"

    
    return render_template('pro5.html', value=value,vid=vid, act=act3,s1=s1)

@app.route('/pro6',methods=['POST','GET'])
def pro6():
    s1=""
    vid = request.args.get('vid')
    act = request.args.get('act')
    value=[]
    
        
    mycursor = mydb.cursor()
    mycursor.execute("SELECT count(*) FROM vt_face where vid=%s",(vid, ))
    cnt = mycursor.fetchone()[0]

    if act is None:
        act=1
        
    act1=int(act)-1
    act2=int(act)+1
    act3=str(act2)
    
    n=10
    if act1<n:
        s1="1"
        mycursor.execute("SELECT * FROM vt_face where vid=%s limit %s,1",(vid, act1))
        value = mycursor.fetchone()
    else:
        s1="2"

    
    return render_template('pro6.html', value=value,vid=vid, act=act3,s1=s1)

@app.route('/pro7',methods=['POST','GET'])
def pro7():
    s1=""
    vid = request.args.get('vid')
    act = request.args.get('act')
    value=[]
    
        
    mycursor = mydb.cursor()
    mycursor.execute("SELECT count(*) FROM vt_face where vid=%s",(vid, ))
    cnt = mycursor.fetchone()[0]

    if act is None:
        act=1
        
    act1=int(act)-1
    act2=int(act)+1
    act3=str(act2)
    
    n=10
    if act1<n:
        s1="1"
        mycursor.execute("SELECT * FROM vt_face where vid=%s limit %s,1",(vid, act1))
        value = mycursor.fetchone()
    else:
        s1="2"

    
    return render_template('pro7.html', value=value,vid=vid, act=act3,s1=s1)


##MiDAS - Distance Estimation
def process(device, model, model_type, image, input_size, target_size, optimize, use_camera):
    
    global first_execution

    if "openvino" in model_type:
        if first_execution or not use_camera:
            print(f"    Input resized to {input_size[0]}x{input_size[1]} before entering the encoder")
            first_execution = False

        sample = [np.reshape(image, (1, 3, *input_size))]
        prediction = model(sample)[model.output(0)][0]
        prediction = cv2.resize(prediction, dsize=target_size,
                                interpolation=cv2.INTER_CUBIC)
    else:
        sample = torch.from_numpy(image).to(device).unsqueeze(0)

        if optimize and device == torch.device("cuda"):
            if first_execution:
                print("  Optimization to half-floats activated. Use with caution, because models like Swin require\n"
                      "  float precision to work properly and may yield non-finite depth values to some extent for\n"
                      "  half-floats.")
            sample = sample.to(memory_format=torch.channels_last)
            sample = sample.half()

        if first_execution or not use_camera:
            height, width = sample.shape[2:]
            print(f"    Input resized to {width}x{height} before entering the encoder")
            first_execution = False

        prediction = model.forward(sample)
        prediction = (
            torch.nn.functional.interpolate(
                prediction.unsqueeze(1),
                size=target_size[::-1],
                mode="bicubic",
                align_corners=False,
            )
            .squeeze()
            .cpu()
            .numpy()
        )

    return prediction


def create_side_by_side(image, depth, grayscale):
    """
    Take an RGB image and depth map and place them side by side. This includes a proper normalization of the depth map
    for better visibility.

    Args:
        image: the RGB image
        depth: the depth map
        grayscale: use a grayscale colormap?

    Returns:
        the image and depth map place side by side
    """
    depth_min = depth.min()
    depth_max = depth.max()
    normalized_depth = 255 * (depth - depth_min) / (depth_max - depth_min)
    normalized_depth *= 3

    right_side = np.repeat(np.expand_dims(normalized_depth, 2), 3, axis=2) / 3
    if not grayscale:
        right_side = cv2.applyColorMap(np.uint8(right_side), cv2.COLORMAP_INFERNO)

    if image is None:
        return right_side
    else:
        return np.concatenate((image, right_side), axis=1)


def run(input_path, output_path, model_path, model_type="dpt_beit_large_512", optimize=False, side=False, height=None,
        square=False, grayscale=False):
    """Run MonoDepthNN to compute depth maps.

    Args:
        input_path (str): path to input folder
        output_path (str): path to output folder
        model_path (str): path to saved model
        model_type (str): the model type
        optimize (bool): optimize the model to half-floats on CUDA?
        side (bool): RGB and depth side by side in output images?
        height (int): inference encoder image height
        square (bool): resize to a square resolution?
        grayscale (bool): use a grayscale colormap?
    """
    print("Initialize")

    # select device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print("Device: %s" % device)

    model, transform, net_w, net_h = load_model(device, model_path, model_type, optimize, height, square)

    # get input
    if input_path is not None:
        image_names = glob.glob(os.path.join(input_path, "*"))
        num_images = len(image_names)
    else:
        print("No input path specified. Grabbing images from camera.")

    # create output folder
    if output_path is not None:
        os.makedirs(output_path, exist_ok=True)

    print("Start processing")

    if input_path is not None:
        if output_path is None:
            print("Warning: No output path specified. Images will be processed but not shown or stored anywhere.")
        for index, image_name in enumerate(image_names):

            print("  Processing {} ({}/{})".format(image_name, index + 1, num_images))

            # input
            original_image_rgb = utils.read_image(image_name)  # in [0, 1]
            image = transform({"image": original_image_rgb})["image"]

            # compute
            with torch.no_grad():
                prediction = process(device, model, model_type, image, (net_w, net_h), original_image_rgb.shape[1::-1],
                                     optimize, False)

            # output
            if output_path is not None:
                filename = os.path.join(
                    output_path, os.path.splitext(os.path.basename(image_name))[0] + '-' + model_type
                )
                if not side:
                    utils.write_depth(filename, prediction, grayscale, bits=2)
                else:
                    original_image_bgr = np.flip(original_image_rgb, 2)
                    content = create_side_by_side(original_image_bgr*255, prediction, grayscale)
                    cv2.imwrite(filename + ".png", content)
                utils.write_pfm(filename + ".pfm", prediction.astype(np.float32))

    else:
        with torch.no_grad():
            fps = 1
            video = VideoStream(0).start()
            time_start = time.time()
            frame_index = 0
            while True:
                frame = video.read()
                if frame is not None:
                    original_image_rgb = np.flip(frame, 2)  # in [0, 255] (flip required to get RGB)
                    image = transform({"image": original_image_rgb/255})["image"]

                    prediction = process(device, model, model_type, image, (net_w, net_h),
                                         original_image_rgb.shape[1::-1], optimize, True)

                    original_image_bgr = np.flip(original_image_rgb, 2) if side else None
                    content = create_side_by_side(original_image_bgr, prediction, grayscale)
                    cv2.imshow('MiDaS Depth Estimation - Press Escape to close window ', content/255)

                    if output_path is not None:
                        filename = os.path.join(output_path, 'Camera' + '-' + model_type + '_' + str(frame_index))
                        cv2.imwrite(filename + ".png", content)

                    alpha = 0.1
                    if time.time()-time_start > 0:
                        fps = (1 - alpha) * fps + alpha * 1 / (time.time()-time_start)  # exponential moving average
                        time_start = time.time()
                    print(f"\rFPS: {round(fps,2)}", end="")

                    if cv2.waitKey(1) == 27:  # Escape key
                        break

                    frame_index += 1
        print()

    print("Finished")
###Feature extraction & Classification
def CNN_process(self):
        
        train_data_preprocess = ImageDataGenerator(
                rescale = 1./255,
                shear_range = 0.2,
                zoom_range = 0.2,
                horizontal_flip = True)

        test_data_preprocess = (1./255)

        train = train_data_preprocess.flow_from_directory(
                'dataset/training',
                target_size = (128,128),
                batch_size = 32,
                class_mode = 'binary')

        test = train_data_preprocess.flow_from_directory(
                'dataset/test',
                target_size = (128,128),
                batch_size = 32,
                class_mode = 'binary')

        ## Initialize the Convolutional Neural Net

        # Initialising the CNN
        cnn = Sequential()

        # Step 1 - Convolution
        # Step 2 - Pooling
        cnn.add(Conv2D(32, (3, 3), input_shape = (128, 128, 3), activation = 'relu'))
        cnn.add(MaxPooling2D(pool_size = (2, 2)))

        # Adding a second convolutional layer
        cnn.add(Conv2D(32, (3, 3), activation = 'relu'))
        cnn.add(MaxPooling2D(pool_size = (2, 2)))

        # Step 3 - Flattening
        cnn.add(Flatten())

        # Step 4 - Full connection
        cnn.add(Dense(units = 128, activation = 'relu'))
        cnn.add(Dense(units = 1, activation = 'sigmoid'))

        # Compiling the CNN
        cnn.compile(optimizer = 'adam', loss = 'binary_crossentropy', metrics = ['accuracy'])

        history = cnn.fit_generator(train,
                                 steps_per_epoch = 250,
                                 epochs = 25,
                                 validation_data = test,
                                 validation_steps = 2000)

        plt.plot(history.history['acc'])
        plt.plot(history.history['val_acc'])
        plt.title('Model Accuracy')
        plt.ylabel('accuracy')
        plt.xlabel('epoch')
        plt.legend(['train', 'test'], loc='upper left')
        plt.show()

        plt.plot(history.history['loss'])
        plt.plot(history.history['val_loss'])
        plt.title('Model Loss')
        plt.ylabel('loss')
        plt.xlabel('epoch')
        plt.legend(['train', 'test'], loc='upper left')
        plt.show()

        test_image = image.load_img('\\dataset\\', target_size=(128,128))
        test_image = image.img_to_array(test_image)
        test_image = np.expand_dims(test_image, axis=0)
        result = cnn.predict(test_image)
        print(result)

        if result[0][0] == 1:
                print('feature extracted and classified')
        else:
                print('none')

def CNN():
    #Lets start by loading the Cifar10 data
    (X, y), (X_test, y_test) = cifar10.load_data()

    #Keep in mind the images are in RGB
    #So we can normalise the data by diving by 255
    #The data is in integers therefore we need to convert them to float first
    X, X_test = X.astype('float32')/255.0, X_test.astype('float32')/255.0

    #Then we convert the y values into one-hot vectors
    #The cifar10 has only 10 classes, thats is why we specify a one-hot
    #vector of width/class 10
    y, y_test = u.to_categorical(y, 10), u.to_categorical(y_test, 10)

    #Now we can go ahead and create our Convolution model
    model = Sequential()
    #We want to output 32 features maps. The kernel size is going to be
    #3x3 and we specify our input shape to be 32x32 with 3 channels
    #Padding=same means we want the same dimensional output as input
    #activation specifies the activation function
    model.add(Conv2D(32, (3, 3), input_shape=(32, 32, 3), padding='same',
                     activation='relu'))
    #20% of the nodes are set to 0
    model.add(Dropout(0.2))
    #now we add another convolution layer, again with a 3x3 kernel
    #This time our padding=valid this means that the output dimension can
    #take any form
    model.add(Conv2D(32, (3, 3), activation='relu', padding='valid'))
    #maxpool with a kernet of 2x2
    model.add(MaxPooling2D(pool_size=(2, 2)))
    #In a convolution NN, we neet to flatten our data before we can
    #input it into the ouput/dense layer
    model.add(Flatten())
    #Dense layer with 512 hidden units
    model.add(Dense(512, activation='relu'))
    #this time we set 30% of the nodes to 0 to minimize overfitting
    model.add(Dropout(0.3))
    #Finally the output dense layer with 10 hidden units corresponding to
    #our 10 classe
    model.add(Dense(10, activation='softmax'))
    #Few simple configurations
    model.compile(loss='categorical_crossentropy',
                  optimizer=SGD(momentum=0.5, decay=0.0004), metrics=['accuracy'])
    #Run the algorithm!
    model.fit(X, y, validation_data=(X_test, y_test), epochs=25,
              batch_size=512)
    #Save the weights to use for later
    model.save_weights("cifar10.hdf5")
    #Finally print the accuracy of our model!
    print("Accuracy: &2.f%%" %(model.evaluate(X_test, y_test)[1]*100))

@app.route('/logout')
def logout():
    # remove the username from the session if it is there
    #session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/monitor', methods=['GET', 'POST'])
def monitor():
    if 'username' in session:
        uname = session['username']
    return render_template('monitor.html')

@app.route('/analyze', methods=['GET', 'POST'])
def analyze():
    txt=""
    f2=open("mess.txt","r")
    fexp=f2.read()
    f2.close()
    if fexp is None:
        txt=""
    else:
        txt="1"
        
    return render_template('analyze.html',txt=txt,fexp=fexp)
def get_image_size():
    img = cv2.imread('gestures/1/100.jpg', 0)
    return img.shape

def get_num_of_classes():
    return len(glob('gestures/*'))

@app.route('/verify_face',methods=['POST','GET'])
def verify_face():
    msg=""
    ss=""
    uname=""
    act=""
    if request.method=='GET':
        act = request.args.get('act')
 
    ff1=open("mess2.txt","w")
    ff1.write("")
    ff1.close()

    ff1=open("mess3.txt","w")
    ff1.write("")
    ff1.close()

    ff1=open("mess4.txt","w")
    ff1.write("")
    ff1.close()

                
    return render_template('verify_face.html',msg=msg)

@app.route('/process',methods=['POST','GET'])
def process():
    msg=""
    ss=""
    uname=""
    act=""
    det=""
    
 
    if request.method=='GET':
        act = request.args.get('act')

    ff3=open("img.txt","r")
    mcnt=ff3.read()
    ff3.close()
    
    mcnt1=int(mcnt)
    print(mcnt1)

    ff=open("result.txt","r")
    det=ff.read()
    ff.close()

    ff=open("mess2.txt","r")
    mes2=ff.read()
    ff.close()

    ff=open("mess3.txt","r")
    mes3=ff.read()
    ff.close()

    ff=open("mess4.txt","r")
    mes4=ff.read()
    ff.close()

    mess=mes4+" "+mes2+" "+mes3
    print(mess)
    
    
    return render_template('process.html',msg=msg,act=act,mcnt1=mcnt1,det=det,mess=mess)

# Load DETR model and COCO labels
def DETR_Model():
    model = torch.hub.load('facebookresearch/detr', 'detr_resnet50', pretrained=True)
    model.eval()
    COCO_CLASSES = [
        'N/A', 'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train',
        'truck', 'boat', 'traffic light', 'fire hydrant', 'N/A', 'stop sign', 'parking meter', 'bench'
        # full list has 91 classes
    ]

    # Load image
    url = "https://images.unsplash.com/photo-1601758123927-03e10c77b1b7"
    image = Image.open(BytesIO(requests.get(url).content))

    # Transform image
    transform = T.Compose([
        T.Resize(800),
        T.ToTensor(),
        T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    img_tensor = transform(image).unsqueeze(0)  # Add batch dimension

    # Forward pass
    with torch.no_grad():
        outputs = model(img_tensor)

    # Convert outputs
    probabilities = outputs['pred_logits'].softmax(-1)[0, :, :-1]  # ignore last class
    boxes = outputs['pred_boxes'][0]  # [x_center, y_center, w, h] normalized

    # Filter predictions with confidence > 0.7
    threshold = 0.7
    keep = probabilities.max(-1).values > threshold
    boxes = boxes[keep]
    labels = probabilities[keep].argmax(-1)

    # Convert normalized boxes to image coordinates
    img_w, img_h = image.size
    boxes[:, :2] = boxes[:, :2] - 0.5 * boxes[:, 2:]  # convert center to top-left
    boxes[:, 0] *= img_w
    boxes[:, 1] *= img_h
    boxes[:, 2] *= img_w
    boxes[:, 3] *= img_h

    # Plot
    fig, ax = plt.subplots(1, figsize=(12, 8))
    ax.imshow(image)
    for box, label in zip(boxes, labels):
        x, y, w, h = box
        rect = patches.Rectangle((x, y), w, h, linewidth=2, edgecolor='r', facecolor='none')
        ax.add_patch(rect)
        ax.text(x, y-10, COCO_CLASSES[label], color='red', fontsize=12, weight='bold')
    plt.show()



#######
def gen2(camera):
    while True:
        frame = camera.get_frame()
    

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
@app.route('/video_feed2')
def video_feed2():

    return Response(gen2(VideoCamera2()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')
##########
def gen(camera):

    while True:
        frame = camera.get_frame()
    

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

    
@app.route('/video_feed')
def video_feed():
    
    return Response(gen(VideoCamera()),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

#########
if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
