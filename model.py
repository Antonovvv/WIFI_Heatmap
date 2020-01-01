# -*- coding:utf-8 -*-
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
import sys
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import numpy as np

from UI.draw import *


class GLWindow(QOpenGLWidget):
    VIEW = np.array([-0.8, 0.8, -0.8, 0.8, 1.0, 1000.0])  # 视景体的left/right/bottom/top/near/far六个面
    SCALE_K = np.array([1.0, 1.0, 1.0])         # 模型缩放比例
    EYE = np.array([0.0, 5.0, 20.0])            # 眼睛的位置（默认z轴的正方向）
    LOOK_AT = np.array([0.0, 0.0, 0.0])         # 瞄准方向的参考点（默认在坐标原点）
    EYE_UP = np.array([0.0, 4.0, 0.0])          # 定义对观察者而言的上方（默认y轴的正方向）
    WIN_W, WIN_H = 960, 680                     # 保存窗口宽度和高度的变量
    LEFT_IS_DOWNED = False                      # 鼠标左键被按下
    MOUSE_X, MOUSE_Y = 0, 0                     # 考察鼠标位移量时保存的起始位置
    dx, dy, dz = 0, 0, 0                        # 观察点平移偏移量

    def __init__(self, building, parent=None):
        super(GLWindow, self).__init__(parent)
        self.DIST, self.PHI, self.THETA = self.get_posture()  # 眼睛与观察目标之间的距离、仰角、方位角
        self.building = building
        self.sources = []
        self.active_source = 0
        # self.grabKeyboard()

    def initializeGL(self):
        glClearColor(0, 0, 0, 1.0)
        glEnable(GL_DEPTH_TEST)     # 开启深度测试，实现遮挡关系
        glDepthFunc(GL_LEQUAL)      # 设置深度测试函数,GL_LEQUAL只是选项之一

        glutInit()
        displayMode = GLUT_DOUBLE | GLUT_ALPHA | GLUT_DEPTH
        glutInitDisplayMode(displayMode)

    def get_posture(self):
        dist = np.sqrt(np.power((self.EYE-self.LOOK_AT), 2).sum())
        if dist > 0:
            # 仰角和方向角
            phi = np.arcsin((self.EYE[1]-self.LOOK_AT[1])/dist)
            theta = np.arcsin((self.EYE[0]-self.LOOK_AT[0])/(dist*np.cos(phi)))
        else:
            phi = 0.0
            theta = 0.0
        return dist, phi, theta

    def paintGL(self):
        # 设置透明显示
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        # 清除屏幕及深度缓存
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        # 设置投影（透视投影）
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()

        width = self.WIN_W
        height = self.WIN_H
        view = self.VIEW
        if width > height:
            glFrustum(view[0] * width / height, view[1] * width / height, view[2], view[3], view[4], view[5])
        else:
            glFrustum(view[0], view[1], view[2] * height / width, view[3] * height / width, view[4], view[5])

        # 设置模型视图
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        # 几何变换
        scale = self.SCALE_K
        glScale(scale[0], scale[1], scale[2])

        # 设置视点
        eye = self.EYE
        eye_up = self.EYE_UP
        look_at = self.LOOK_AT
        gluLookAt(
            eye[0], eye[1], eye[2],
            look_at[0], look_at[1], look_at[2],
            eye_up[0], eye_up[1], eye_up[2]
        )

        # 设置视口
        glViewport(0, 0, width, height)

        # 平移
        glTranslatef(self.dx, self.dy, self.dz)

        sqare = [[-1, -1], [-1, 1], [1, 1], [1, -1]]
        # color_wall = [0.9, 0.9, 0.9]
        color_land = [0.9, 0.9, 0.9]
        land = 100.0

        # 绘制地面
        glBegin(GL_POLYGON)
        for i in range(4):
            glColor4f(color_land[0], color_land[1], color_land[2], 1.0)
            glVertex3f(sqare[i][0] * land, 0, sqare[i][1] * land)
        glEnd()

        # 绘制房间
        for i in range(self.building.floors):
            for j in range(self.building.rooms):
                if self.building.rooms % 2 == 0:
                    pos_x = (self.building.room_size[0] / 2 + self.building.wall_thickness) * pow(-1, j) * (2 * (j // 2) + 1)
                else:
                    pos_x = (self.building.room_size[0] + 2 * self.building.wall_thickness) * pow(-1, j + 1) * ((j + 1) // 2)
                pos_y = (self.building.room_size[2] + self.building.floor_thickness) * i
                draw_wall(position=[pos_x, pos_y, 0], size=self.building.room_size, thickness=self.building.wall_thickness)
            floor_height = self.building.room_size[2] + (self.building.room_size[2] + self.building.floor_thickness) * i
            floor_length = self.building.rooms * (self.building.room_size[0] + 2 * self.building.wall_thickness)
            floor_width = self.building.room_size[1] + 2 * self.building.wall_thickness
            draw_floor(position=[0, floor_height, 0], length=floor_length, width=floor_width, thickness=self.building.floor_thickness)

        # 绘制信号强度球面
        for source in self.sources:
            glPushMatrix()
            glTranslatef(source.position[0], source.position[1], source.position[2])
            # r = 0.01
            for i in range(source.wave):
                r = (i + 1) * source.span
                s = source.power - source.damp(r)
                alpha = np.power(10, (s + 50) / 20) / 8
                if s > -50:
                    glColor4f(0.75, 0, 0, alpha)
                elif -50 > s > -70:
                    glColor4f(0.75 + (-s - 50) / 80, 0, 0, alpha)
                elif -70 > s > -80:  # 红到黄
                    glColor4f(1, (-s - 70) / 10, 0, alpha)
                elif -80 > s > -90:  # 黄到绿
                    glColor4f(1 - (-s - 80) / 10, 1, 0, alpha)
                else:
                    # r += (-s) / 200
                    break
                # r += (-s) / 200
                # glutWireSphere(r, 32, 32)

                sphere = gluNewQuadric()
                gluSphere(sphere, r, 16, 16)
            glPopMatrix()

        # 切换缓冲区，以显示绘制内容
        # glutSwapBuffers()

    def resizeGL(self, width, height):
        self.WIN_W, self.WIN_H = width, height
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.MOUSE_X, self.MOUSE_Y = e.x(), e.y()
            self.LEFT_IS_DOWNED = True

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.LEFT_IS_DOWNED = False

    def mouseMoveEvent(self, e):
        if self.LEFT_IS_DOWNED:
            dx = self.MOUSE_X - e.x()
            dy = e.y() - self.MOUSE_Y
            self.MOUSE_X, self.MOUSE_Y = e.x(), e.y()

            self.PHI += 2 * np.pi * dy / self.WIN_H
            self.PHI %= 2 * np.pi
            self.THETA += 2 * np.pi * dx / self.WIN_W
            self.THETA %= 2 * np.pi
            r = self.DIST * np.cos(self.PHI)

            self.EYE[1] = self.DIST * np.sin(self.PHI)
            self.EYE[0] = r * np.sin(self.THETA)
            self.EYE[2] = r * np.cos(self.THETA)

            if 0.5 * np.pi < self.PHI < 1.5 * np.pi:
                self.EYE_UP[1] = -1.0
            else:
                self.EYE_UP[1] = 1.0

            self.update()

    def wheelEvent(self, e):
        if e.angleDelta().y() >= 120:
            self.EYE = self.LOOK_AT + (self.EYE - self.LOOK_AT) * 0.95
            self.DIST, self.PHI, self.THETA = self.get_posture()
            self.update()
        elif e.angleDelta().y() <= -120:
            self.EYE = self.LOOK_AT + (self.EYE - self.LOOK_AT) / 0.95
            self.DIST, self.PHI, self.THETA = self.get_posture()
            self.update()

    def keyPressEvent(self, e):
        key = e.key()
        mod = e.modifiers()
        speed = 0.4
        if key in [Qt.Key_W, Qt.Key_A, Qt.Key_S, Qt.Key_D, Qt.Key_Space, Qt.Key_C]:
            if key == Qt.Key_W:
                self.dz += speed
            elif key == Qt.Key_S:
                self.dz -= speed
            elif key == Qt.Key_A:
                self.dx += speed
            elif key == Qt.Key_D:
                self.dx -= speed
            elif key == Qt.Key_Space:
                self.dy -= speed
            elif key == Qt.Key_C:
                self.dy += speed
            self.update()
        if self.active_source >= 0:
            active = self.active_source
            if key in [Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right]:
                if mod == Qt.ControlModifier:
                    if key == Qt.Key_Up:
                        self.sources[active].position[1] += speed
                    elif key == Qt.Key_Down:
                        self.sources[active].position[1] -= speed
                else:
                    if key == Qt.Key_Up:
                        self.sources[active].position[2] -= speed
                    elif key == Qt.Key_Down:
                        self.sources[active].position[2] += speed
                    elif key == Qt.Key_Left:
                        self.sources[active].position[0] -= speed
                    elif key == Qt.Key_Right:
                        self.sources[active].position[0] += speed
                self.update()


class Building:
    def __init__(self, floors=1, rooms=1, floor_thickness=0.3, room_length=10.0,
                 room_width=5.0, room_height=5.0, wall_thickness=0.10):
        self.floors = floors
        self.rooms = rooms
        self.floor_thickness = floor_thickness
        self.room_size = [room_length, room_width, room_height]
        self.wall_thickness = wall_thickness


class Source:
    FREQS = [5000, 2400]        # 发射频段
    DAMPING = [20, 25]          # 衰减补偿
    SPAN = [0.2, 0.3]           # 波间隔
    WAVE_BY_POWER = [10, 5]     # 波数与发射功率之比

    def __init__(self, power=15, type=0, pos_x=0.0, pos_y=0.0, pos_z=0.0):
        self.freq = self.FREQS[type],
        self.power = power,
        self.type = type,
        self.position = [pos_x, pos_y, pos_z]
        self.wave = self.WAVE_BY_POWER[type] * power      # 波数量
        self.span = self.SPAN[type]
        self.damping = self.DAMPING[type]

    def damp(self, r):
        # 衰减值(dBm)
        return self.damping + 32.45 + 20 * np.log10(self.freq) + 20 * np.log10(r / 1000)


if __name__ == '__main__':
    glutInit()
    displayMode = GLUT_DOUBLE | GLUT_ALPHA | GLUT_DEPTH
    glutInitDisplayMode(displayMode)

    app = QApplication(sys.argv)

    building = Building(floors=5, rooms=5, floor_thickness=1, room_length=12, room_width=6, room_height=5, wall_thickness=0.2)
    glwindow = GLWindow(building)
    source = Source()
    glwindow.sources.append(source)

    glwindow.setGeometry(200, 200, 960, 680)
    glwindow.show()
    sys.exit(app.exec_())
