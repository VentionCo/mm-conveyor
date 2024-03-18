import time

class Timer():
    def __init__(self,delay : float = 1.0):
        """
        Parameters
        ----------
        delay : float, optional, defaults to 1.0
            Time in seconds until done() returns true
        """
        self.__delay = delay
        self.__start_time = 0.0
        self.__pause_start_time = 0.0 
        self.__pause_duration = 0.0
        self.started = False
        self.paused = False

    def start(self):
        """
        Start (or restart) timer execution

        Parameters
        ----------
        none

        Returns
        ----------
        none
        """
        self.started = True
        self.paused = False
        self.__pause_duration = 0.0
        self.__start_time = float(time.perf_counter())
    
    def pause(self):
        """
        Pause the timer only if it is not already paused
        """
        if not self.paused and self.started:
            self.__pause_start_time = float(time.perf_counter())
            self.paused = True

    def unpause(self):
        """
        Un-Pause the timer only if it was paused.
        """
        if self.paused:
            self.__pause_duration +=  float(time.perf_counter()) - self.__pause_start_time
            self.paused = False

    def stop(self):
        """
        Stop timer execution
        
        Parameters
        ----------
        none

        Returns
        ----------
        none
        """
        self.started = False
        self.__start_time = 0.0
        self.__pause_start_time = 0.0 
        self.__pause_duration = 0.0
        self.paused = False

    def elapsedTimeSinceStart(self):
        """
        Check how much time has been elapsed since last start() - paused duration
        
        Parameters
        ----------
        none

        Returns
        ----------
        float
            time since last start in seconds, returns 0.0 if timer not started
        """
        if self.started:
            if not self.paused:
                return float(time.perf_counter()) - self.__start_time - self.__pause_duration 
            else:
                return float(time.perf_counter()) - self.__start_time - self.__pause_duration - (float(time.perf_counter())  - self.__pause_start_time)

        else:
            return 0.0

    def done(self):
        """
        Check if the timer is completed
        
        Parameters
        ----------
        none

        Returns
        ----------
        bool
            True if timer has reached delay time, False if timer not started or not finished
        """
        if self.started:
            return abs((float(time.perf_counter())) - self.__start_time - self.__pause_duration) >= self.__delay
        else: 
            return False

class Pulse():

    def __init__(self, period : float = 1.0):
        """
        Parameters
        ----------
        period : float, optional, default to 1.0
            Time in seconds of a full cycle
        """
        self.__timer = Timer(period/2)
        self.__status = False

    def run(self):
        """
        Run the Pulse, starts at false, becomes true after half a cycle
        
        Parameters
        ----------
        none

        Returns
        ----------
        bool
            True the pulse is on high state, False if pulse is in the low state
        """
        if not self.__timer.started:
            self.__timer.start()
        
        if self.__timer.done():
            self.__status = not self.__status
            self.__timer.start()

        return self.__status

if __name__ == "__main__":
    #Code used to debug and test the library
    timerA = Timer(4)
    timerA.start()
    print(f"Starting time:\t{float(time.perf_counter())}")

    time.sleep(1)
    print(f"Time Elaspsed 1: {timerA.elapsedTimeSinceStart()}")
    timerA.pause()
    time.sleep(1)
    print(f"Time Elaspsed 2: {timerA.elapsedTimeSinceStart()}")

    if timerA.paused:
        print("Unpause Timer")
        timerA.unpause()
    else:
        # print("Timer Restart")
        # timerA.start()
        print(f"Time Elaspsed 3: {timerA.elapsedTimeSinceStart()}")

    time.sleep(1)
    timerA.pause()
    time.sleep(2)
    print(f"Time Elaspsed 4: {timerA.elapsedTimeSinceStart()}")

    if timerA.paused:
        print("Unpause Timer")
        timerA.unpause()
        print(f"Time Elaspsed 5: {timerA.elapsedTimeSinceStart()}")

    else:
        print("Restart Timer ")
        timerA.start()

    while True:
        if timerA.done():
            print ("Timer is complete")
            break
    print(f"Stop time:\t{float(time.perf_counter())}")
    print("Exiting Timer Debug Code....")