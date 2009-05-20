'''
Created on 28-Apr-2009

@author: kevala
'''
root = Tk()
    root.title('Create Archive')
    root.resizable(FALSE,FALSE)
    root.geometry('250x150')
    
    frameButtons = Frame(root)
    frameSessionIdEntry = Frame(root)
    frameDeviceCodeEntry = Frame(root)
    
    buttonCreate = Button(frameButtons, text='Create Archive')
    buttonCancel = Button(frameButtons, text='Cancel', command=root.quit)
    labelSessionId = Label(frameSessionIdEntry, text='Session ID: ')
    labelDeviceCode = Label(frameDeviceCodeEntry, text='Device Code: ')
    entrySessionId = Entry(frameSessionIdEntry, width=10)
    entryDeviceCode = Entry(frameDeviceCodeEntry, width=10)
    createPreviews = IntVar()
    checkCreatePreviews = Checkbutton(root, text='Create Preview Files', variable=createPreviews)
    checkCreatePreviews.select()
    
    labelSessionId.pack(side=LEFT)
    labelDeviceCode.pack(side=LEFT)
    entrySessionId.pack(side=RIGHT)
    entryDeviceCode.pack(side=RIGHT)
    buttonCreate.pack(side=LEFT)
    buttonCancel.pack(side=RIGHT)
    
    frameSessionIdEntry.pack(fill=Y, expand=1)
    frameDeviceCodeEntry.pack(fill=Y, expand=1)
    checkCreatePreviews.pack(fill=Y, expand=1)
    frameButtons.pack(fill=Y, expand=1)
    
    
    
    root.mainloop()