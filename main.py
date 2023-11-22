import tkinter as tk
import cv2
import PIL.Image, PIL.ImageTk
import time
import numpy as np
import file_access

def degrees2clock(angle_deg):
    #Convert degrees into hours and minutes (o'clocks)
    a = angle_deg
    if a<0:
        a+=360
    hour = np.floor(a * 12/360.0)
    minutes = a*12/360.0 - hour
    if hour==0:
        hour = 12.0
    minutes = minutes*60
    return "%i:%s"%(hour,("%i"%minutes).zfill(2))

class App:
    def __init__(self, window, window_title, video_source=0):

        # Open file
        self.dataLog = file_access.DataLog(starting_epoch=1696112663136)

        self.play_video = True
        self.auto_update_slider = True
        self.window = window
        self.window.title(window_title)
        self.video_source = video_source
        # open video source (by default this will try to open the computer webcam)
        self.vid = MyVideoCapture(self.video_source)
        # Create a canvas that can fit the above video source size
        self.width, self.height = self.vid.get_dimensions()
        self.homographic_points = [[self.width-5,5],[self.width-5,self.height-5],[5,self.height-5],[5,5]]
        self.homographic_point_move = None
        self.distance_normalized_to_table_length = 0
        self.distance_points = [[5,5],[10,10]]
        self.canvas = tk.Canvas(window, width = self.width, height = self.height)
        self.canvas.bind("<Button-1>",self.canvas_mouse_left_down)
        self.canvas.bind("<B1-Motion>", self.canvas_mouse_left_moved)
        self.canvas.bind("<ButtonRelease-1>", self.canvas_mouse_left_up)
        self.canvas.bind("<Button-3>", self.canvas_mouse_right_down)
        self.canvas.bind("<B3-Motion>", self.canvas_mouse_right_moved)
        self.canvas.bind("<ButtonRelease-3>", self.canvas_mouse_right_up)
        self.canvas.pack()

        self.build_video_controls(window)


        # Text boxes
        self.txt_distance_value = tk.StringVar()
        self.txt_distance=tk.Entry(window, width=10, textvariable=self.txt_distance_value)
        self.txt_distance.pack(side=tk.LEFT)

        self.txt_frame_time_value = tk.StringVar()
        self.txt_frame_time = tk.Entry(window, width=10, textvariable=self.txt_frame_time_value)
        self.txt_frame_time.pack(side=tk.LEFT)

        self.txt_degrees_value = tk.StringVar()
        self.txt_degrees = tk.Entry(window, width=10, textvariable=self.txt_degrees_value)
        self.txt_degrees.pack(side=tk.LEFT)

        self.txt_rpm_value = tk.StringVar()
        self.txt_rpm = tk.Entry(window, width=10, textvariable=self.txt_rpm_value)
        self.txt_rpm.pack(side=tk.LEFT)






        self.delay = 15
        self.after_handle = None
        self.update()
        self.window.mainloop()

    def build_video_controls(self, window):
        frame = tk.Frame(window)
        frame.pack()

        # Position slider
        current_frame, total_frames = self.vid.get_frame_number()
        self.sld_position = tk.Scale(frame, from_=0, to_=total_frames, orient='horizontal',
                                     length=self.width)
        self.sld_position.bind("<B1-Motion>", self.slider_moved)
        self.sld_position.bind("<Button-1>", self.slider_down)
        self.sld_position.bind("<ButtonRelease-1>", self.slider_up)
        self.sld_position.pack(anchor=tk.CENTER, expand=True)

        # Button that lets the user take a snapshot
        frame_buttons = tk.Frame(frame)
        frame_buttons.pack(anchor=tk.CENTER, expand=True)
        self.btn_snapshot = tk.Button(frame_buttons, text="Snapshot", width=10, command=self.snapshot)
        self.btn_snapshot.pack(side=tk.LEFT)
        self.btn_rewind = tk.Button(frame_buttons, text="<<", width=5, command=self.rewind)
        self.btn_rewind.pack(side=tk.LEFT)
        self.btn_rewind_single = tk.Button(frame_buttons, text="<", width=5, command=self.rewind_single)
        self.btn_rewind_single.pack(side=tk.LEFT)
        self.btn_pause = tk.Button(frame_buttons, text="||", width=5, command=self.pause)
        self.btn_pause.pack(side=tk.LEFT)
        self.btn_play = tk.Button(frame_buttons, text="|>", width=5, command=self.play)
        self.btn_play.pack(side=tk.LEFT)
        self.btn_forward_single = tk.Button(frame_buttons, text=">", width=5, command=self.forward_single)
        self.btn_forward_single.pack(side=tk.LEFT)
        self.btn_forward = tk.Button(frame_buttons, text=">>", width=5, command=self.forward)
        self.btn_forward.pack(side=tk.LEFT)

    def draw_on_canvas(self):

        #Draw homographic polygon
        line_width = 2
        a = self.homographic_points
        b = self.distance_points
        line_color = 'cyan'
        self.draw_line_on_canvas("hom1", a[0][0], a[0][1], a[1][0], a[1][1], line_width, line_color)
        line_color = 'blue'
        self.draw_line_on_canvas("hom2", a[1][0], a[1][1], a[2][0], a[2][1], line_width, line_color)
        line_color = 'cyan'
        self.draw_line_on_canvas("hom3", a[2][0], a[2][1], a[3][0], a[3][1], line_width, line_color)
        line_color = 'blue'
        self.draw_line_on_canvas("hom4", a[3][0], a[3][1], a[0][0], a[0][1], line_width, line_color)

        line_color = 'red'
        self.draw_line_on_canvas("dist", b[0][0], b[0][1], b[1][0], b[1][1], line_width, line_color)

        #Draw ball graphic
        ang = self.shot_data['deg']
        r = 45
        center = 50
        x = r * np.sin(ang*np.pi/180)
        y = -r * np.cos(ang*np.pi/180)

        line_color = 'white'
        self.draw_oval_on_canvas("ball_circle",center, center, r, line_width, line_color)

        line_color = 'red'
        self.draw_line_on_canvas("spin_angle",center,center,center+x,center+y,line_width,line_color)




    def draw_line_on_canvas(self,line_name,x1,y1,x2,y2,line_width,line_color):
        #Updates lines if they already exist rather than wasting memory redrawing lines over and over again
        item_id = self.canvas.find_withtag(line_name)
        if item_id:
            self.canvas.coords(line_name,x1,y1,x2,y2)
            self.canvas.tag_raise(line_name)
        else:
            self.canvas.create_line(x1,y1,x2,y2,width=line_width,fill=line_color,tags=line_name)

    def draw_oval_on_canvas(self,line_name,x,y,r,line_width,line_color):
        #Updates lines if they already exist rather than wasting memory redrawing lines over and over again
        x1 = x-r
        x2 = x+r
        y1 = y-r
        y2 = y+r
        item_id = self.canvas.find_withtag(line_name)
        if item_id:
            self.canvas.coords(line_name,x1,y1,x2,y2)
            self.canvas.tag_raise(line_name)
        else:
            self.canvas.create_oval(x1,y1,x2,y2,width=line_width,fill=line_color,tags=line_name)

    def snapshot(self):
        # Get a frame from the video source
        ret, frame = self.vid.get_frame()
        if ret:
            cv2.imwrite("frame-" + time.strftime("%d-%m-%Y-%H-%M-%S") + ".jpg", cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))

    def copy_frame_to_canvas(self):

        # Get a frame from the video source
        ret, frame = self.vid.get_frame()
        if ret:
            self.photo = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(frame))
            self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)

        frame_time_seconds = self.vid.get_frame_time()
        self.txt_frame_time_value.set('%.3f'%frame_time_seconds)
        self.shot_data = self.dataLog.get_next_shot_data(frame_time_seconds)

        return ret

    def update_shot_data_info(self):
        data = self.shot_data
        if data is not None:
            if 'rpm' in data:
                self.txt_rpm_value.set('%.2f'%self.shot_data['rpm'])
            else:
                self.txt_rpm_value.set('')

            if 'deg' in data:
                clock = degrees2clock(self.shot_data['deg'])
                self.txt_degrees_value.set(clock)
            else:
                self.txt_degrees_value.set('')


    def update(self):
        if self.play_video:
            ret = self.copy_frame_to_canvas()
            if ret:
                frame,total = self.vid.get_frame_number()
                if self.auto_update_slider:
                    self.sld_position.set(frame)

        self.draw_on_canvas()
        self.update_shot_data_info()
        self.after_handle = self.window.after(self.delay, self.update)

    def move_frame_delta(self, frames):
        frame, total = self.vid.get_frame_number()
        self.vid.goto_frame(frame + frames - 1)

    def slider_down(self, event):
        self.auto_update_slider = False

    def slider_moved(self, event):
        position_frame = self.sld_position.get()
        self.vid.goto_frame(position_frame)
        if not self.play_video:
            ret = self.copy_frame_to_canvas()

    def slider_up(self, event):
        self.auto_update_slider = True

    def pause(self):
        self.play_video = False

    def play(self):
        if not self.play_video:
            self.play_video = True

    def rewind(self):
        self.move_frame_delta(-100)

    def rewind_single(self):
        self.move_frame_delta(-1)

    def forward(self):
        self.move_frame_delta(100)

    def forward_single(self):
        self.move_frame_delta(1)

    def canvas_mouse_left_down(self, event):
        x, y = event.x, event.y
        self.distance_points[0][0] = x
        self.distance_points[0][1] = y
        self.distance_points[1][0] = x
        self.distance_points[1][1] = y
        self.update_homographic_distance()

    def canvas_mouse_left_moved(self, event):
        x, y = event.x, event.y
        self.distance_points[1][0] = x
        self.distance_points[1][1] = y
        self.update_homographic_distance()

    def canvas_mouse_left_up(self, event):
        x, y = event.x, event.y
        self.distance_points[1][0] = x
        self.distance_points[1][1] = y
        self.update_homographic_distance()

    def canvas_mouse_right_down(self, event):
        #Choose homographic point closest to mouse
        x1, y1 = event.x, event.y
        r = None
        index = 0
        for i in range(0,4):
            x2 = self.homographic_points[i][0]
            y2 = self.homographic_points[i][1]
            dist = np.sqrt((x1-x2)**2+(y1-y2)**2)
            if r is None:
                r = dist
                index = i
            else:
                if dist<r:
                    r=dist
                    index = i
        self.homographic_point_move = index
        self.update_homographic_distance()

    def canvas_mouse_right_moved(self, event):
        x, y = event.x, event.y
        i = self.homographic_point_move
        self.homographic_points[i][0] = x
        self.homographic_points[i][1] = y
        self.update_homographic_distance()

    def canvas_mouse_right_up(self, event):
        self.homographic_point_move = None
        self.update_homographic_distance()

    def update_homographic_distance(self):
        self.distance_normalized_to_table_length = self.get_homographic_distance(1,0.5)
        self.txt_distance_value.set('%.3f'%self.distance_normalized_to_table_length)

    def get_homographic_distance(self, scaleX, scaleY):
        #Calculates the distance selected based on the homographic bounding polygon
        #ScaleX and ScaleY are the units to multiply the X and Y axes by

        pts1 = np.array(self.homographic_points, dtype = 'f')
        ratio = 1.6
        self._pH = np.sqrt((pts1[2][0] - pts1[1][0]) * (pts1[2][0] - pts1[1][0]) + (pts1[2][1] - pts1[1][1]) * (
                pts1[2][1] - pts1[1][1]))
        self._pW = ratio * self._pH
        self._pts2 = np.float32([[pts1[0][0], pts1[0][1]], [pts1[0][0] + self._pW, pts1[0][1]],
                                 [pts1[0][0] + self._pW, pts1[0][1] + self._pH],
                                 [pts1[0][0], pts1[0][1] + self._pH]])
        self._M = cv2.getPerspectiveTransform(pts1, self._pts2)

        points = np.array([[[self.distance_points[0][0],self.distance_points[0][1]]],
                           [[self.distance_points[1][0],self.distance_points[1][1]]]])

        hpoints = self._M.dot(np.array([[x, y, 1] for [[x, y]] in points]).T)
        hpoints /= hpoints[2]
        result = np.array([[[x, y]] for [x, y] in hpoints[:2].T])

        x1 = scaleX * (result[0][0][0] - self._pts2[0][0]) / self._pW
        y1 = scaleY * (result[0][0][1] - self._pts2[0][1]) / self._pH
        x2 = scaleX * (result[1][0][0] - self._pts2[0][0]) / self._pW
        y2 = scaleY * (result[1][0][1] - self._pts2[0][1]) / self._pH

        distance_normalized = np.sqrt((x1-x2)**2+(y1-y2)**2)
        return distance_normalized



class MyVideoCapture:
    def __init__(self, video_source=0):
        # Open the video source
        self._current_frame = 0
        self._vid = cv2.VideoCapture(video_source)
        self._total_frames = int(self._vid.get(cv2.CAP_PROP_FRAME_COUNT))
        if not self._vid.isOpened():
            raise ValueError("Unable to open video source", video_source)
        # Get video source width and height
        self._width = self._vid.get(cv2.CAP_PROP_FRAME_WIDTH)
        self._height = self._vid.get(cv2.CAP_PROP_FRAME_HEIGHT)

    def get_frame_time(self):
        return self._vid.get(cv2.CAP_PROP_POS_MSEC)/1000

    def get_frame(self):
        if self._vid.isOpened():
            ret, frame = self._vid.read()
            if ret:
                # Return a boolean success flag and the current frame converted to BGR
                obj = (ret, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            else:
                obj = (ret, None)
        else:
            obj = (ret, None)

        self._current_frame = self._vid.get(cv2.CAP_PROP_POS_FRAMES)
        return obj

    def get_dimensions(self):
        return (self._width, self._height)

    def get_frame_number(self):
        return (self._current_frame, self._total_frames)

    def goto_frame(self, frame_number):
        self._vid.set(cv2.CAP_PROP_POS_FRAMES, frame_number)

    # Release the video source when the object is destroyed
    def __del__(self):
        if self._vid.isOpened():
            self._vid.release()

if __name__=='__main__':

    # Create a window and pass it to the Application object
    App(tk.Tk(), "Tkinter and OpenCV", "digiball_demo_stream_1.mp4")