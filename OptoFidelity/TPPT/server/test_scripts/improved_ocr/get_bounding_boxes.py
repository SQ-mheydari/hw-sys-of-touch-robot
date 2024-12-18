"""
Really simple script that will help with getting bounding boxes from the image

Install dependencies and run the script. Marking bounding box requires 'mouse down' - 'drag' - 'mouse up'
when window gets closed then coordinates for all bounding boxes will be printed
"""
import pygame, sys
from PIL import Image
import queue
pygame.init()


def displayImage(screen, px, topleft):
    screen.blit(px, px.get_rect())
    if topleft:
        pygame.draw.rect(screen, 0, pygame.Rect(topleft[0], topleft[1], pygame.mouse.get_pos()[0] - topleft[0], pygame.mouse.get_pos()[1] - topleft[1]))
    pygame.display.flip()


def setup(path):
    px = pygame.image.load(path)
    screen = pygame.display.set_mode(px.get_rect()[2:])
    screen.blit(px, px.get_rect())
    pygame.display.flip()
    return screen, px


def mainLoop(screen, px, queue):
    topleft = None
    bottomright = None
    runProgram = True
    while runProgram:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                runProgram = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                topleft = event.pos
            elif event.type == pygame.MOUSEBUTTONUP:
                bottomright = event.pos
                queue.put(topleft + bottomright)
                topleft = None
        displayImage(screen, px, topleft)
    return None


if __name__ == "__main__":
    image_path = r'C:\Users\lwalac\Desktop\tesseract\ocr test 20200429\camera_image.png'
    screen, px = setup(image_path)
    q = queue.Queue()
    mainLoop(screen, px, q)
    while True:
        try:
            left, upper, right, lower = q.get(timeout=1)
            print('({}, {}, {}, {}),'.format(left, upper, right, lower))
        except queue.Empty:
            break
    pygame.quit()
    sys.exit()
