import pygame
import sys

import pylsl, numpy as np, utils #, os


DEVICE_ID = "MUSE_938C"
CHANNELS = [0, 3]  # TP9 and TP10 electrodes.
FREQUENCY_BANDS = ["Delta", "Theta", "Alpha", "Beta"]

# Constants for the EEG signal real-time processing.
SAMPLING_RATE = 256
BUFFER_LENGTH = 5
EPOCH_LENGTH = 1
OVERLAP_LENGTH = 0.5

# Arbitrary values to determine movement.
DELTA_BLINK_DIFFERENCE_PSD = 0.5
DELTA_BLINK_PSD = 1.8

# Resolves the EEG stream on the lab network and starts aquiring data.
streams = pylsl.resolve_byprop("type", "EEG", timeout = 2)
inlet = pylsl.StreamInlet(streams[0], max_chunklen = 12)

# EEG and PSD data buffer.
eeg_buffer = np.zeros((int(SAMPLING_RATE*BUFFER_LENGTH), 1))
epochs = int(np.floor((BUFFER_LENGTH - EPOCH_LENGTH) / (EPOCH_LENGTH - OVERLAP_LENGTH + 1)))
psd_buffer = np.zeros((epochs, 4))
buffers = [[eeg_buffer, eeg_buffer, eeg_buffer], [psd_buffer, psd_buffer, psd_buffer]]

i = 0
num_blinks = 0

#print("Starting in 10 seconds...")
#time.sleep(10)

pygame.init()
font = pygame.font.Font('freesansbold.ttf', 32)

WHITE = (255, 255, 255)
BLUE = (0, 0, 128)

CLOCK = pygame.time.Clock()
SCREEN = pygame.display.set_mode((800, 800))
pygame.display.set_caption("Jump When You Blink!")

X_POSITION, Y_POSITION = 400, 660

jumping = False

Y_GRAVITY = 1
JUMP_HEIGHT = 20
Y_VELOCITY = JUMP_HEIGHT

STANDING_SURFACE = pygame.transform.scale(pygame.image.load("assets/mario_standing.png"), (48, 64))
JUMPING_SURFACE = pygame.transform.scale(pygame.image.load("assets/mario_jumping.png"), (48, 64))
BACKGROUND = pygame.image.load("assets/background.png")

mario_rect = STANDING_SURFACE.get_rect(center=(X_POSITION, Y_POSITION))

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
    
    if not jumping:
        for channel in range(len(CHANNELS)):

            all_eeg_data, timestamp = inlet.pull_chunk(timeout = 1, max_samples = int((EPOCH_LENGTH - OVERLAP_LENGTH) * SAMPLING_RATE))
            # Remove the EEG data from the channels that are not being analyzed.
            channel_eeg_data = np.array(all_eeg_data)[:, CHANNELS[channel]]

            # Update the EEG buffer and apply a notch filter from the utils file.
            buffers[0][channel], filter_state = utils.update_buffer(buffers[0][channel], channel_eeg_data, notch = True, filter_state = None)

            # Get newest samples from the buffer.
            latest_eeg_data = utils.get_last_data(buffers[0][channel], EPOCH_LENGTH * SAMPLING_RATE)

            # Compute the PSD for each channel and update the PSD buffer.
            band_powers = utils.compute_band_powers(latest_eeg_data, SAMPLING_RATE)
            buffers[1][channel], _ = utils.update_buffer(buffers[1][channel], np.asarray([band_powers]))


        TP9_PSD_DELTA = buffers[1][0][-1][FREQUENCY_BANDS.index("Delta")]
        TP10_PSD_DELTA = buffers[1][1][-1][FREQUENCY_BANDS.index("Delta")]
        DELTA_SUM = TP9_PSD_DELTA + TP10_PSD_DELTA

        TP9_PSD_DELTA_PREVIOUS = buffers[1][0][-2][FREQUENCY_BANDS.index("Delta")]
        TP10_PSD_DELTA_PREVIOUS = buffers[1][1][-2][FREQUENCY_BANDS.index("Delta")]
        DELTA_SUM_PREVIOUS =  TP9_PSD_DELTA_PREVIOUS + TP10_PSD_DELTA_PREVIOUS

        print("i: {}, Delta Power TP9: {}, Delta Power TP10: {}, Delta Total: {}".format(str(i),str(TP9_PSD_DELTA),str(TP10_PSD_DELTA),str(DELTA_SUM)))

        if i == 0 and DELTA_SUM >= DELTA_BLINK_PSD:
            jumping = True
            print("BLINK DETECTED!")
            num_blinks +=1

        if DELTA_SUM - DELTA_SUM_PREVIOUS >= DELTA_BLINK_DIFFERENCE_PSD and not i == 0:
            jumping = True
            print("BLINK DETECTED!")
            num_blinks +=1

        i += 1


    SCREEN.blit(BACKGROUND, (0, 0))

    text = font.render('Blinks Detected: '+ str(num_blinks), True, WHITE, BLUE)
    textRect = text.get_rect()
    textRect.center = (635, 30)
    SCREEN.blit(text, textRect)

    if jumping:
        Y_POSITION -= Y_VELOCITY
        Y_VELOCITY -= Y_GRAVITY
        if Y_VELOCITY < -JUMP_HEIGHT:
            jumping = False
            Y_VELOCITY = JUMP_HEIGHT
        mario_rect = JUMPING_SURFACE.get_rect(center=(X_POSITION, Y_POSITION))
        SCREEN.blit(JUMPING_SURFACE, mario_rect)
    else:
        mario_rect = STANDING_SURFACE.get_rect(center=(X_POSITION, Y_POSITION))
        SCREEN.blit(STANDING_SURFACE, mario_rect)


    pygame.display.update()
    CLOCK.tick(240)
