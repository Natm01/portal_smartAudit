import React, { useState } from 'react';

const ApplicationCard = ({ application, onClick }) => {
  const [isHovered, setIsHovered] = useState(false);

  const getIcon = (iconType) => {
    const iconProps = "w-6 h-6";

    const icons = {
      document: (
        <svg className={iconProps} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M9 12H15M9 16H15M17 21H7C5.89543 21 5 20.1046 5 19V5C5 3.89543 5.89543 3 7 3H12.5858C12.851 3 13.1054 3.10536 13.2929 3.29289L18.7071 8.70711C18.8946 8.89464 19 9.149 19 9.41421V19C19 20.1046 18.1046 21 17 21Z" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M13 3V8C13 8.55228 13.4477 9 14 9H19" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      ),
      chart: (
        <svg className={iconProps} viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M3 3v18h18" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
          <path d="M18.7 8l-5.1 5.2-2.8-2.7L7 14.3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      ),
    };
    return icons[iconType] || icons.document;
  };

  return (
    <div
      className={`relative group cursor-pointer transition-all duration-300 ease-out
        bg-white rounded-2xl shadow-md hover:shadow-lg
        border border-transparent hover:border-purple-300
        p-6 w-full max-w-sm flex flex-col justify-between overflow-hidden
        focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2
        ${isHovered ? 'bg-purple-50/30' : ''}
      `}
      onClick={() => onClick?.(application)}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      tabIndex={0}
      role="button"
      aria-label={`Acceder a ${application.name}`}
    >
      <div className="absolute -top-10 -right-10 w-32 h-32 bg-purple-100 rounded-full mix-blend-multiply opacity-20 pointer-events-none"></div>

      <div className="w-12 h-12 rounded-xl bg-[#7B3DF0] text-white flex items-center justify-center shadow-md mb-4">
        {getIcon(application.icon)}
      </div>

      <h3 className="text-sm font-semibold text-gray-900 mb-1 leading-tight">
        {application.name}
      </h3>
      <p className="text-[11px] text-gray-600">
        {application.description}
      </p>

      <div className={`absolute bottom-3 right-3 text-purple-600 text-[10px] font-medium transition-opacity duration-300 ${isHovered ? 'opacity-100' : 'opacity-0'}`}>
        Acceder →
      </div>
    </div>
  );
};

export default ApplicationCard;
