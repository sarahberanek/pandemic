#!/usr/bin/env python

import copy
import readline
import sys

class SimpleCompleter(object):

  def __init__(self, options):
    self.options = sorted(options)
    return

  def complete(self, text, state):
    response = None
    if state == 0:
      # This is the first time for this text, so build a match list.
      if text:
        self.matches = [s for s in self.options if s and s.startswith(text)]
      else:
        self.matches = self.options[:]

    # Return the state'th item from the match list, if we have that many.
    try:
      response = self.matches[state]
    except IndexError:
      response = None
    return response

class PandemicInfections(object):

  def __init__(self, cities_file, state_filename='state.txt'):
    self.cities = []
    self.stack = []
    self.cards_drawn = []
    self.state_filename = state_filename
    self.setup(cities_file)

  def setup(self, cities_file):
    self.read_cities(cities_file)
    self.stack = [copy.copy(self.cities)]
    # Register the completer function and bind tab
    options = copy.copy(self.cities)
    options = sorted(set(options), key=options.index)
    options.append('READ')
    options.append('EPIDEMIC')
    readline.set_completer(SimpleCompleter(options).complete)
    readline.parse_and_bind('tab: complete')

  def read_cities(self, filename):
    # Read input file with city names.
    self.cities = []
    with open(filename, 'r') as f:
      for line in f:
        line = line.strip('\n')
        if not line or line.startswith('#'):
          continue
        if '*' in line:
          n, city = line.split('*')
          self.cities += int(n) * [city]
        else:
          self.cities += [line]

  def draw_card(self, line):
    # Draw card from the top of the stack and add it to the discard pile.
    self.cards_drawn.append(line)
    assert(self.stack[-1])
    self.stack[-1].remove(line)
    if not self.stack[-1]:
      self.stack.pop()

  def epidemic(self):
    question = 'Which city was drawn from the bottom in the Epidemic? '
    impossible = 'This is impossible!'
    # Draw card from front of the stack ("the bottom")
    line = input(question)
    assert(self.stack)
    front_pile = self.stack[0]
    while not line in front_pile:
      print(impossible)
      line = input(question)
    self.cards_drawn.append(line)
    # Remove card from front pile and remove it from the stack if it is now empty.
    front_pile.remove(line)
    if not front_pile:
      del self.stack[0]
    # Push discard pile on stack and reset it.
    self.stack.append(sorted(self.cards_drawn))
    self.cards_drawn = []

  def print_state(self, f=sys.stdout):
    # Print the draw deck with sections
    i = 0
    print('', file=f)
    print('############################', file=f)
    print('###       The Deck       ###', file=f)
    for x in self.stack:
      for city in x:
        print(i, city, file=f)
      i += 1
      if i != len(self.stack):
        print('----------------------------', file=f)
    print('############################', file=f)
    # Print the discard pile
    print('', file=f)
    print('############################', file=f)
    print('###       Discard        ###', file=f)
    for city in self.cards_drawn:
      print('d', city, file=f)
    print('############################', file=f)

  def write_state(self):
    # Write the current state to disk
    with open(self.state_filename, 'w') as f:
      self.print_state(f=f)

  def read_state(self):
    # Read the current state from disk
    self.stack = []
    self.cards_drawn = []
    prev_level = 0
    temp = []
    with open(self.state_filename, 'r') as f:
      for line in f:
        line = line.strip('\n')
        if line.startswith('#') or line.startswith('-') or not line:
          continue
        level, city = line.split(' ')
        if level == 'd':
          self.cards_drawn.append(city)
        else:
          if level == prev_level:
            temp.append(city)
          else:
            if temp:
              self.stack.append(temp)
            temp = []
            temp.append(city)
            prev_level = level
      if temp:
        self.stack.append(temp)

  def calculate_probability(self, city, N):
    # Calculate the probability to draw city at least once in N draws.
    toy_stack = copy.deepcopy(self.stack)
    toy_pile = toy_stack.pop()
    total_prob = 0.0
    for i in range(N):
      total = len(toy_pile)
      count = toy_pile.count(city)
      probability = count/total
      total_prob += (1.0 - total_prob) * probability
      if total_prob == 1.0:
        return total_prob
      for x in toy_pile:
        if x != city:
          toy_pile.remove(x)
          break
      else:
        assert(False)
      if not toy_pile:
        toy_pile = toy_stack.pop()
    return total_prob

  def print_probabilities(self):
    # Print probabilities
    print()
    print('%-15s %6d %6d %6d %6d %6d' % ('Name', 1, 2, 3, 4, 5))
    print('--------------------------------------------------')
    for x in sorted(set(self.cities), key=self.cities.index):
      line = '%-15s ' % x
      for n in range(1,6):
        p = self.calculate_probability(x, n)
        line += "%5.1f%% " % (100.0 * p)
      print(line)

  def run(self):
    # The main input loop
    question = 'Please enter the name of the city which was drawn or "EPIDEMIC/READ": '
    impossible = 'This is impossible!'
    while True:
      # Get new input
      print()
      line = input(question)
      while line != 'EPIDEMIC' and line != 'READ' and not line in self.stack[-1]:
        print(impossible)
        line = input(question)
      # Process
      if line == 'READ':
        self.read_state()
      elif line == 'EPIDEMIC':
        self.epidemic()
      else:
        self.draw_card(line)
      # Print current state and probabilities, write state to disk
      self.print_state()
      self.print_probabilities()
      self.write_state()

# Start the input loop
cities_file = sys.argv[1]
output_file = sys.argv[2] if len(sys.argv) > 2 else 'state.txt'
p = PandemicInfections(cities_file=cities_file, state_filename=output_file)
p.run()
