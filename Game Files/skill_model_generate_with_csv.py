
"""
 Generate score distribution for a set of variants for given difficulty levels.
 * Four types of error models used.
   1) Simple probability model - A random value between 0 and 1 is chosen and if it is greater than the given difficulty value the bird performs a jump.
   2) Normal distribution model - A list of values drawn from a normal distribution of zero mean and a standard deviation proportional to the difficulty is created.
      For each value of the nn output, a random value is drawn from this list and added to it.
   3) Uniform distribution model - Same as normal distribution model but here a uniform distribution is used.
   4) Normal distribution-Probability model - The same procedure as normal distribution model is used initially.
      A difficulty value is set between 0 and 1.
      A random value is drawn from the list created using normal distribution(Error value). Also a random value is chosen between 0 and 1 and if this value is less than the 
      difficulty value the error value is added to the output of nn.
"""
import pygame
import random
import os
import time
import neat
import visualize
import pickle
import csv
import sys
import math
import pandas as pd
import numpy as np
import time

pygame.font.init()  # init font

WIN_WIDTH = 600
WIN_HEIGHT = 800
FLOOR = 730
GAP = 250 #250
SEPERATION =  100 #SEPERATION <0,200>
VELOCITY = 40 #VELOCITY <20,60>
PIPE_VELOCITY  = 6 #PIPE_VELOCITY <4,13>
JUMP_VELOCITY = -12 #JUMP_VELOCITY <-5,-12>
GRAVITY = 3  #GRAVITY <2,3>
FLOOR = math.floor(730 * WIN_HEIGHT / 800)

STAT_FONT = pygame.font.SysFont("comicsans", 50)
END_FONT = pygame.font.SysFont("comicsans", 70)
DRAW_LINES = False
WIN = pygame.display.set_mode((WIN_WIDTH, WIN_HEIGHT))
pygame.display.set_caption("Flappy Bird")
file_name_prefix = os.environ.get('file_name_prefix', "")
if(file_name_prefix!=""):
    print("Loaded environment variable "+file_name_prefix)
    file_name_prefix+="_"

# reached_limit = True
pipe_img = pygame.transform.scale2x(pygame.image.load(os.path.join("imgs","pipe.png")).convert_alpha())
bg_img = pygame.transform.scale(pygame.image.load(os.path.join("imgs","bg.png")).convert_alpha(), (600, 900))
bird_images = [pygame.transform.scale2x(pygame.image.load(os.path.join("imgs","bird" + str(x) + ".png"))) for x in range(1,4)]
base_img = pygame.transform.scale2x(pygame.image.load(os.path.join("imgs","base.png")).convert_alpha())
# address = ('localhost', 6005)     # family is deduced to be 'AF_INET'
# listener = Listener(address, authkey=b'secret password')
# conn = listener.accept()
pickle_file=""
gen = 0
score = 0
sample = 600

#Normal distribution-Probability model
ulimit = 1.5
llimit = -1.5
difficulties = [0.9]
j_error_list_normal = None #Normal distribution model - If the list is used varying standard deviation alone
j_error_list_uniform = np.random.uniform(llimit,ulimit,1000) #Uniform distribution model
j_error_parameters = None

score_list = []
for i in difficulties:   # for n probability
    score_list.append([])

class Bird:
    """
    Bird class representing the flappy bird
    """
    MAX_ROTATION = 25
    IMGS = bird_images
    ROT_VEL = 20
    ANIMATION_TIME = 5

    def __init__(self, x, y):
        """
        Initialize the object
        :param x: starting x pos (int)
        :param y: starting y pos (int)
        :return: None
        """
        self.x = x
        self.y = y
        self.tilt = 0  # degrees to tilt
        self.tick_count = 0
        self.vel = 0
        self.height = self.y
        self.img_count = 0
        self.img = self.IMGS[0]

    def jump(self):
        """
        make the bird jump
        :return: None
        """
        self.vel = JUMP_VELOCITY #JUMP_VELOCITY
        self.tick_count = 0
        self.height = self.y

    def move(self):
        """
        make the bird move
        :return: None
        """
        self.tick_count += 1

        # for downward acceleration
        displacement = self.vel*(self.tick_count) + 0.5*(GRAVITY)*(self.tick_count)**2  # calculate displacement
       
        # terminal velocity
        if displacement >= 16:
            displacement = (displacement/abs(displacement)) * 16

        if displacement < 0:
            displacement -= 2

        self.y = self.y + displacement

        if displacement < 0 or self.y < self.height + 50:  # tilt up
            if self.tilt < self.MAX_ROTATION:
                self.tilt = self.MAX_ROTATION
        else:  # tilt down
            if self.tilt > -90:
                self.tilt -= self.ROT_VEL

    def draw(self, win):
        """
        draw the bird
        :param win: pygame window or surface
        :return: None
        """
        self.img_count += 1

        # For animation of bird, loop through three images
        if self.img_count <= self.ANIMATION_TIME:
            self.img = self.IMGS[0]
        elif self.img_count <= self.ANIMATION_TIME*2:
            self.img = self.IMGS[1]
        elif self.img_count <= self.ANIMATION_TIME*3:
            self.img = self.IMGS[2]
        elif self.img_count <= self.ANIMATION_TIME*4:
            self.img = self.IMGS[1]
        elif self.img_count == self.ANIMATION_TIME*4 + 1:
            self.img = self.IMGS[0]
            self.img_count = 0

        # so when bird is nose diving it isn't flapping
        if self.tilt <= -80:
            self.img = self.IMGS[1]
            self.img_count = self.ANIMATION_TIME*2


        # tilt the bird
        blitRotateCenter(win, self.img, (self.x, self.y), self.tilt)

    def get_mask(self):
        """
        gets the mask for the current image of the bird
        :return: None
        """
        return pygame.mask.from_surface(self.img)


class Pipe():
    """
    represents a pipe object
    """

    def __init__(self, x):
        """
        initialize pipe object
        :param x: int
        :param y: int
        :return" None
        """
        self.VEL = PIPE_VELOCITY
        self.x = x+SEPERATION -100
        self.height = 0

        # where the top and bottom of the pipe is
        self.top = 0
        self.bottom = 0

        self.PIPE_TOP = pygame.transform.flip(pipe_img, False, True)
        self.PIPE_BOTTOM = pipe_img

        self.passed = False

        self.set_height()

    def set_height(self):
        """
        set the height of the pipe, from the top of the screen
        :return: None
        """
        self.height = random.randrange(90, 410)
        # self.height = random.randrange(90, 660-GAP)

        self.top = self.height - self.PIPE_TOP.get_height()
        self.bottom = self.height + GAP

    def move(self):
        """
        move pipe based on vel
        :return: None
        """
        self.x -= self.VEL
     

    def draw(self, win):
        """
        draw both the top and bottom of the pipe
        :param win: pygame window/surface
        :return: None
        """
        # draw top
        win.blit(self.PIPE_TOP, (self.x, self.top))
        # draw bottom
        win.blit(self.PIPE_BOTTOM, (self.x, self.bottom))


    def collide(self, bird, win):
        """
        returns if a point is colliding with the pipe
        :param bird: Bird object
        :return: Bool
        """
        bird_mask = bird.get_mask()
        top_mask = pygame.mask.from_surface(self.PIPE_TOP)
        bottom_mask = pygame.mask.from_surface(self.PIPE_BOTTOM)
        top_offset = (self.x - bird.x, self.top - round(bird.y))
        bottom_offset = (self.x - bird.x, self.bottom - round(bird.y))

        b_point = bird_mask.overlap(bottom_mask, bottom_offset)
        t_point = bird_mask.overlap(top_mask,top_offset)

        if b_point or t_point:
            return True

        return False

class Base:
    """
    Represnts the moving floor of the game
    """
    VEL = 5
    WIDTH = base_img.get_width()
    IMG = base_img

    def __init__(self, y):
        """
        Initialize the object
        :param y: int
        :return: None
        """
        self.y = y
        self.x1 = 0
        self.x2 = self.WIDTH

    def move(self):
        """
        move floor so it looks like its scrolling
        :return: None
        """
        self.x1 -= self.VEL
        self.x2 -= self.VEL
        if self.x1 + self.WIDTH < 0:
            self.x1 = self.x2 + self.WIDTH

        if self.x2 + self.WIDTH < 0:
            self.x2 = self.x1 + self.WIDTH

    def draw(self, win):
        """
        Draw the floor. This is two images that move together.
        :param win: the pygame surface/window
        :return: None
        """
        win.blit(self.IMG, (self.x1, self.y))
        win.blit(self.IMG, (self.x2, self.y))


def blitRotateCenter(surf, image, topleft, angle):
    """
    Rotate a surface and blit it to the window
    :param surf: the surface to blit to
    :param image: the image surface to rotate
    :param topLeft: the top left position of the image
    :param angle: a float value for angle
    :return: None
    """
    rotated_image = pygame.transform.rotate(image, angle)
    new_rect = rotated_image.get_rect(center = image.get_rect(topleft = topleft).center)

    surf.blit(rotated_image, new_rect.topleft)

def draw_window(win, birds, pipes, base, score, gen, pipe_ind):
    """
    draws the windows for the main game loop
    :param win: pygame window surface
    :param bird: a Bird object
    :param pipes: List of pipes
    :param score: score of the game (int)
    :param gen: current generation
    :param pipe_ind: index of closest pipe
    :return: None
    """
    if gen == 0:
        gen = 1
    win.blit(bg_img, (0,0))

    for pipe in pipes:
        pipe.draw(win)

    base.draw(win)
    for bird in birds:
        # draw lines from bird to pipe
        if DRAW_LINES:
            try:
                pygame.draw.line(win, (255,0,0), (bird.x+bird.img.get_width()/2, bird.y + bird.img.get_height()/2), (pipes[pipe_ind].x + pipes[pipe_ind].PIPE_TOP.get_width()/2, pipes[pipe_ind].height), 5)
                pygame.draw.line(win, (255,0,0), (bird.x+bird.img.get_width()/2, bird.y + bird.img.get_height()/2), (pipes[pipe_ind].x + pipes[pipe_ind].PIPE_BOTTOM.get_width()/2, pipes[pipe_ind].bottom), 5)
            except:
                pass
        # draw bird
        bird.draw(win)

    # score
    score_label = STAT_FONT.render("Score: " + str(score),1,(255,255,255))
    win.blit(score_label, (WIN_WIDTH - score_label.get_width() - 15, 10))

    # sample
    score_label = STAT_FONT.render("Sample: " + str(gen-1),1,(255,255,255))
    win.blit(score_label, (10, 10))

    # alive
    score_label = STAT_FONT.render("Alive: " + str(len(birds)),1,(255,255,255))
    win.blit(score_label, (10, 50))

    pygame.display.update()


def eval_genomes(genomes, config,pickle_file,difficulty):
    """
    runs the simulation of the current population of
    birds and sets their fitness based on the distance they
    reach in the game.
    """
    global WIN, gen ,reached_limit
    win = WIN
    gen += 1

    # start by creating lists holding the genome itself, the
    # neural network associated with the genome and the
    # bird object that uses that network to play
    nets = []
    birds = []
    ge = []
    for genome_id, genome in genomes:
        # genome.fitness = 0  # start with fitness level of 0
        net = neat.nn.FeedForwardNetwork.create(genome, config)
        nets.append(net)
        birds.append(Bird(230,350))
        ge.append(genome)

    base = Base(FLOOR)
    pipes = [Pipe(700)]
    score = 0

    clock = pygame.time.Clock()

    run = True
    start = time.time()
    while run and len(birds) > 0:
        clock.tick(40)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False
                pygame.quit()
                quit()
                break

        pipe_ind = 0
        if len(birds) > 0:
            if len(pipes) > 1 and birds[0].x > pipes[0].x + pipes[0].PIPE_TOP.get_width():  # determine whether to use the first or second
                pipe_ind = 1                                                                 # pipe on the screen for neural network input

        for x, bird in enumerate(birds):  # give each bird a fitness of 0.1 for each frame it stays alive
            # ge[x].fitness += 0.1
            bird.move()


            #Simple probabilty model 
            #difficulty = 0.6
            #j_val = random.uniform(0,1)
            # if j_val>difficulty:
            #     output = nets[birds.index(bird)].activate((bird.y, abs(bird.y - pipes[pipe_ind].height), abs(bird.y - pipes[pipe_ind].bottom)))
            #     if output[0] > 0.5:  # we use a tanh activation function so result will be between -1 and 1. if over 0.5 jump
            #     if time.time()-start>0.125:
            #         start = time.time()
            #         bird.jump()

            # send bird location, top pipe location and bottom pipe location and determine from network whether to jump or not
            # output = nets[birds.index(bird)].activate((bird.y, abs(bird.y - pipes[pipe_ind].height), abs(bird.y - pipes[pipe_ind].bottom)))
            x_distance = abs(pipes[pipe_ind].x - bird.x)
            tp_y_distance = abs(bird.y - pipes[pipe_ind].height)
            bp_y_distance = abs(bird.y - pipes[pipe_ind].bottom)
            tp_distance = math.sqrt(x_distance**2 + tp_y_distance**2)
            bp_distance = math.sqrt(x_distance**2 + bp_y_distance**2)
            output = nets[birds.index(bird)].activate((bird.y, tp_distance, bp_distance))

            #Normal distribution-Probability model
            error_prob = random.uniform(0,1)
            if error_prob<difficulty:
                j_error = random.choice(j_error_list_uniform)  
                output[0]+=j_error

            if output[0] > 0.5:  # we use a tanh activation function so result will be between -1 and 1. if over 0.5 jump
                if time.time()-start>0.125:
                    start = time.time()
                    bird.jump()


        base.move()

        rem = []
        add_pipe = False
        for pipe in pipes:
            pipe.move()
            # check for collision
            for bird in birds:
                if pipe.collide(bird, win):
                    # ge[birds.index(bird)].fitness -= 1
                    nets.pop(birds.index(bird))
                    ge.pop(birds.index(bird))
                    birds.pop(birds.index(bird))

            if pipe.x + pipe.PIPE_TOP.get_width() < 0:
                rem.append(pipe)

            if not pipe.passed and pipe.x < bird.x:
                pipe.passed = True
                add_pipe = True

        if add_pipe:
            score += 1
            # for genome in ge:
            #     genome.fitness += 5
            pipes.append(Pipe(WIN_WIDTH))

        for r in rem:
            pipes.remove(r)

        for bird in birds:
            if bird.y + bird.img.get_height() - 10 >= FLOOR or bird.y < -50:
                nets.pop(birds.index(bird))
                ge.pop(birds.index(bird))
                birds.pop(birds.index(bird))

        draw_window(WIN, birds, pipes, base, score, gen, pipe_ind)
        
        # break if score gets large enough
        if (score > 100):
            break
    print("score: ",score,difficulty)
    score_list[difficulties.index(difficulty)].append(score) # for n probability
    return score

def run(config_file,pickle_file):
    # reached_limit = True
    """
    runs the NEAT algorithm to train a neural network to play flappy bird.
    :param config_file: location of config file
    :return: None
    """
    config = neat.config.Config(neat.DefaultGenome, neat.DefaultReproduction,
                         neat.DefaultSpeciesSet, neat.DefaultStagnation,
                         config_file)

    genome_path = file_name_prefix+"/"+file_name_prefix+'Verified_Pickles/'+ pickle_file
    with open(genome_path, "rb") as f:
        genome = pickle.load(f)
    genomes = [(1, genome)]
    # Create the population, which is the top-level object for a NEAT run.
    for difficulty in difficulties:
        for i in range(sample):
            score = eval_genomes(genomes,config,pickle_file,difficulty)
    df2= pd.DataFrame(dict(zip(difficulties, score_list)),columns=difficulties) # for n probability
    df2.to_csv(csv_file_name, mode='a', header=False, index = False)
    f.close()


def read_variant_data(config_path):
    global WIN,GAP,SEPERATION,VELOCITY,PIPE_VELOCITY,JUMP_VELOCITY,GRAVITY, csv_file_name,j_error_list_normal,j_error_parameters
    # j_error_list_normal = np.random.normal(0, sd, 1000)
    j_error_parameters = [llimit, ulimit, 1000,difficulties]
    if(len(sys.argv)>2):
        print(sys.argv)
        line = sys.argv[1:]
        line = GAP,SEPERATION,VELOCITY,PIPE_VELOCITY,JUMP_VELOCITY,GRAVITY= [ int(i) for i in sys.argv[1:-2]]
        pickle_file = sys.argv[-2] 
        pygame.display.set_caption(",".join(sys.argv[1:-2]))
        # csv_file_name = file_name_prefix+"/"+file_name_prefix+"Scores/"+ pickle_file+ sys.argv[-1]+"_" +str(sd)+'.csv'
        csv_file_name = file_name_prefix+"/"+file_name_prefix+"Scores/"+ pickle_file+ sys.argv[-1]+'.csv'
        print("Variant parameters ",[GAP,SEPERATION,VELOCITY,PIPE_VELOCITY,JUMP_VELOCITY,GRAVITY],csv_file_name)
        with open(csv_file_name,'a') as fd:
            csv_writer = csv.writer(fd, delimiter=',', lineterminator = '\n')
            csv_writer.writerow(line)
            csv_writer.writerow(j_error_parameters)
            csv_writer.writerow(difficulties)
        for i in score_list: # for n probability
            i.clear()
        run(config_path,pickle_file)      
    else:
        print("not enough parameters")

    
if __name__ == '__main__':
    """
    Determine path to configuration file. This path manipulation is
    here so that the script will run successfully regardless of the
    current working directory.
    """
    try:
        local_dir = os.path.dirname(__file__)
        config_path = os.path.join(local_dir, 'config-feedforward.txt')
        read_variant_data(config_path)
    except Exception as e:
        print(e)
        time.sleep(5000)